import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt

from apps.users.permissions import IsAdminRole
from apps.rentals.models import Invoice
from apps.bookings.models import Booking
from .models import Refund, ReconciliationItem, ReconciliationRun, Payment, MpesaTransaction, Payout
from .serializers import (
    PaymentSerializer, STKPushInitiateSerializer, PayoutSerializer, WalletTransactionSerializer,
    PaybillTransactionSerializer, ManualReconcileSerializer,
)
from .mpesa_client import MpesaClient, MpesaError
from .security import is_valid_safaricom_ip
from .services import mark_payment_completed, mark_payment_failed, get_wallet_balance

logger = logging.getLogger('apps.payments')


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class STKPushInitiateView(APIView):
    throttle_scope = 'mpesa'

    def post(self, request):
        serializer = STKPushInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        invoice = None
        booking = None
        if vd.get('invoice_id'):
            invoice = generics.get_object_or_404(Invoice, id=vd['invoice_id'])
        if vd.get('booking_id'):
            booking = generics.get_object_or_404(Booking, id=vd['booking_id'])

        payment = Payment.objects.create(
            payer=request.user,
            invoice=invoice,
            booking=booking,
            method=Payment.Method.MPESA_STK,
            amount=vd['amount'],
            phone_number=vd['phone_number'],
            description=vd.get('description', 'FRIDAH Payment'),
        )

        client = MpesaClient()
        try:
            result = client.stk_push(
                phone_number=vd['phone_number'],
                amount=vd['amount'],
                account_reference=payment.reference,
                transaction_desc=vd.get('description', 'FRIDAH Payment'),
            )
        except MpesaError as e:
            mark_payment_failed(payment, str(e))
            return Response({'success': False, 'error': {'message': str(e)}}, status=status.HTTP_502_BAD_GATEWAY)

        resp = result['response']
        MpesaTransaction.objects.create(
            payment=payment,
            merchant_request_id=resp.get('MerchantRequestID'),
            checkout_request_id=resp.get('CheckoutRequestID'),
            phone_number=vd['phone_number'],
            amount=vd['amount'],
            raw_request=result['payload'],
        )
        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=['status'])

        try:
            from .tasks import poll_stk_status
            poll_stk_status.apply_async(args=[str(payment.id)], countdown=20)
        except Exception as e:
            logger.warning("Could not schedule STK poll task: %s", e)

        return success(
            {'payment': PaymentSerializer(payment).data, 'checkout_request_id': resp.get('CheckoutRequestID')},
            message="STK push sent. Enter your M-Pesa PIN to complete payment.",
        )


class STKPushStatusView(APIView):
    """Frontend polls this to check if the STK push completed (in addition to Celery backend polling)."""

    def get(self, request, payment_id):
        payment = generics.get_object_or_404(Payment, id=payment_id, payer=request.user)
        return success(PaymentSerializer(payment).data)


class MpesaSTKCallbackView(APIView):
    """Safaricom posts STK push results here. No auth — validated via IP allowlist."""
    permission_classes = [AllowAny]
    authentication_classes = []
    # Already gated by is_valid_safaricom_ip() below, which is a much stronger check
    # than a generic per-IP rate limit — and Safaricom can legitimately send many
    # callbacks per hour on real transaction volume, so the platform-wide anon
    # throttle must not apply here or it would start silently dropping real
    # payment confirmations once volume grows.
    throttle_classes = []

    def post(self, request):
        if not is_valid_safaricom_ip(request):
            logger.warning("Rejected M-Pesa callback from untrusted IP")
            return Response(status=403)

        body = request.data.get('Body', {})
        callback = body.get('stkCallback', {})
        checkout_request_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        result_desc = callback.get('ResultDesc')

        try:
            mpesa_txn = MpesaTransaction.objects.select_related('payment').get(checkout_request_id=checkout_request_id)
        except MpesaTransaction.DoesNotExist:
            logger.error("STK callback for unknown CheckoutRequestID: %s", checkout_request_id)
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        mpesa_txn.result_code = result_code
        mpesa_txn.result_desc = result_desc
        mpesa_txn.raw_callback = request.data

        if result_code == 0:
            items = {i['Name']: i.get('Value') for i in callback.get('CallbackMetadata', {}).get('Item', [])}
            mpesa_txn.mpesa_receipt_number = items.get('MpesaReceiptNumber')
            mpesa_txn.transaction_date = str(items.get('TransactionDate', ''))
            mpesa_txn.save()
            mark_payment_completed(
                mpesa_txn.payment, mpesa_receipt=mpesa_txn.mpesa_receipt_number, received_amount=items.get('Amount'),
            )
        else:
            mpesa_txn.save()
            mark_payment_failed(mpesa_txn.payment, reason=result_desc or "Payment cancelled or failed")

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaC2BValidationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Safaricom webhook — see MpesaSTKCallbackView for rationale.

    def post(self, request):
        if not is_valid_safaricom_ip(request):
            return Response(status=403)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaC2BConfirmationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Safaricom webhook — see MpesaSTKCallbackView for rationale.

    def post(self, request):
        if not is_valid_safaricom_ip(request):
            return Response(status=403)
        logger.info("C2B confirmation received: %s", request.data)

        from .models import PaybillTransaction
        from .services import reconcile_paybill_transaction

        data = request.data
        txn, created = PaybillTransaction.objects.get_or_create(
            mpesa_receipt_number=data.get('TransID'),
            defaults=dict(
                transaction_type=data.get('TransactionType', ''),
                transaction_time=data.get('TransTime', ''),
                amount=data.get('TransAmount') or 0,
                business_short_code=data.get('BusinessShortCode', ''),
                bill_ref_number=data.get('BillRefNumber', ''),
                msisdn=data.get('MSISDN', ''),
                first_name=data.get('FirstName', ''),
                middle_name=data.get('MiddleName', ''),
                last_name=data.get('LastName', ''),
                raw_callback=data,
            ),
        )
        if created:
            reconcile_paybill_transaction(txn)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaB2CResultView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Safaricom webhook — see MpesaSTKCallbackView for rationale.

    def post(self, request):
        if not is_valid_safaricom_ip(request):
            return Response(status=403)
        result = request.data.get('Result', {})
        conversation_id = result.get('ConversationID')
        result_code = result.get('ResultCode')
        result_desc = result.get('ResultDesc')

        from django.db import transaction as db_transaction
        from .services import finalize_b2c_result
        with db_transaction.atomic():
            payout = Payout.objects.select_for_update().filter(conversation_id=conversation_id).first()
            if payout is None:
                logger.error("B2C result for unknown ConversationID: %s", conversation_id)
                return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
            params = {p['Key']: p.get('Value') for p in result.get('ResultParameters', {}).get('ResultParameter', [])}
            finalize_b2c_result(payout, result_code, result_desc, params.get('TransactionReceipt'), request.data)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaB2CTimeoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Safaricom webhook — see MpesaSTKCallbackView for rationale.

    def post(self, request):
        logger.warning("B2C timeout callback: %s", request.data)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    filterset_fields = ['status', 'method']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(payer=user).order_by('-created_at')


class WalletBalanceView(APIView):
    def get(self, request):
        from .models import WalletTransaction
        balance = get_wallet_balance(request.user)
        recent = WalletTransaction.objects.filter(user=request.user).order_by('-created_at')[:20]
        return success({
            'balance': balance,
            'recent_transactions': WalletTransactionSerializer(recent, many=True).data,
        })


class PayoutRequestView(APIView):
    """Landlord/provider/host requests a withdrawal of wallet balance to M-Pesa."""

    def post(self, request):
        from django.db import transaction as db_transaction
        from .services import debit_wallet, credit_wallet

        amount = Decimal(str(request.data.get('amount', 0)))
        phone = request.data.get('phone_number')

        if amount <= 0:
            return Response({'success': False, 'error': {'message': 'Invalid amount.'}}, status=400)

        payout = Payout.objects.create(recipient=request.user, amount=amount, phone_number=phone, status=Payout.Status.PENDING)

        # Debit first, atomically and under a row lock (see services.debit_wallet), so two
        # concurrent payout requests can't both pass a balance check before either debit lands.
        try:
            with db_transaction.atomic():
                debit_wallet(request.user, amount, f"Withdrawal requested: {payout.id}", related_payout=payout)
        except ValueError:
            payout.status = Payout.Status.FAILED
            payout.result_desc = "Insufficient balance."
            payout.save(update_fields=['status', 'result_desc'])
            return Response({'success': False, 'error': {'message': 'Invalid amount or insufficient balance.'}}, status=400)

        client = MpesaClient()
        try:
            result = client.b2c_payment(phone_number=phone, amount=amount, remarks=f"FRIDAH payout {payout.id}")
            payout.conversation_id = result.get('ConversationID')
            payout.status = Payout.Status.PROCESSING
            payout.save(update_fields=['conversation_id', 'status'])
        except MpesaError as e:
            # M-Pesa rejected the request outright: refund the wallet since no payout will occur.
            # (If M-Pesa accepted it and later fails asynchronously, MpesaB2CResultView handles
            # that and should credit the wallet back there instead of here.)
            credit_wallet(request.user, amount, f"Payout {payout.id} reversed: request rejected", related_payout=payout)
            payout.status = Payout.Status.FAILED
            payout.result_desc = str(e)
            payout.save(update_fields=['status', 'result_desc'])
            return Response({'success': False, 'error': {'message': str(e)}}, status=502)

        return success(PayoutSerializer(payout).data, message="Payout initiated.")


class PaybillTransactionListView(generics.ListAPIView):
    """Admin queue of raw paybill payments, optionally filtered to unmatched ones needing attention."""
    serializer_class = PaybillTransactionSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['match_status']

    def get_queryset(self):
        from .models import PaybillTransaction
        return PaybillTransaction.objects.all().order_by('-created_at')


class PaybillTransactionReconcileView(APIView):
    """Admin manually matches an unmatched paybill payment to the correct invoice."""
    permission_classes = [IsAdminRole]

    def post(self, request, transaction_id):
        from .models import PaybillTransaction
        from .services import manually_reconcile_paybill_transaction

        serializer = ManualReconcileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        txn = generics.get_object_or_404(PaybillTransaction, id=transaction_id)
        invoice = generics.get_object_or_404(Invoice, id=serializer.validated_data['invoice_id'])

        try:
            txn = manually_reconcile_paybill_transaction(txn, invoice, request.user)
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)

        return success(PaybillTransactionSerializer(txn).data, message="Payment reconciled.")


class PayoutListView(generics.ListAPIView):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payout.objects.all().order_by('-created_at')
        return Payout.objects.filter(recipient=user).order_by('-created_at')


class PaymentMethodListCreateView(generics.ListCreateAPIView):
    from .serializers import PaymentMethodSerializer
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        from .models import PaymentMethod
        return PaymentMethod.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentMethodDeleteView(APIView):
    def delete(self, request, id):
        from .models import PaymentMethod
        method = generics.get_object_or_404(PaymentMethod, id=id, user=request.user)
        method.delete()
        return success(message="Payment method removed.")


class PaymentAllocationListView(generics.ListAPIView):
    from .serializers import PaymentAllocationSerializer
    serializer_class = PaymentAllocationSerializer

    def get_queryset(self):
        from .models import PaymentAllocation
        payment_id = self.kwargs['payment_id']
        payment = generics.get_object_or_404(Payment, id=payment_id)
        if payment.payer_id != self.request.user.id and self.request.user.role != 'admin':
            return PaymentAllocation.objects.none()
        return PaymentAllocation.objects.filter(payment=payment)


class TenantAdvanceListCreateView(generics.ListCreateAPIView):
    from .serializers import TenantAdvanceSerializer
    serializer_class = TenantAdvanceSerializer

    def get_queryset(self):
        from .models import TenantAdvance
        user = self.request.user
        if user.role == 'admin':
            return TenantAdvance.objects.all().order_by('-requested_at')
        if user.role == 'tenant':
            return TenantAdvance.objects.filter(tenant=user).order_by('-requested_at')
        return TenantAdvance.objects.filter(lease__landlord=user).order_by('-requested_at')

    def create(self, request, *args, **kwargs):
        from .serializers import RequestTenantAdvanceSerializer
        from .services import request_tenant_advance
        from apps.rentals.models import Lease, Invoice

        serializer = RequestTenantAdvanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lease = generics.get_object_or_404(Lease, id=data['lease_id'], tenant=request.user)
        invoice = None
        if data.get('invoice_id'):
            invoice = generics.get_object_or_404(Invoice, id=data['invoice_id'], lease=lease)

        advance = request_tenant_advance(
            tenant=request.user, lease=lease, amount=data['amount'], reason=data.get('reason', ''), invoice=invoice,
        )
        from .serializers import TenantAdvanceSerializer
        return success(TenantAdvanceSerializer(advance).data, message="Advance requested.", status_code=status.HTTP_201_CREATED)


class TenantAdvanceApproveView(APIView):
    def post(self, request, id):
        from .models import TenantAdvance
        from .services import approve_tenant_advance
        from .serializers import TenantAdvanceSerializer

        advance = generics.get_object_or_404(TenantAdvance, id=id)
        if advance.lease.landlord_id != request.user.id and request.user.role != 'admin':
            return Response({'success': False, 'error': {'message': 'Not authorized to approve this advance.'}}, status=403)
        advance = approve_tenant_advance(advance, approved_by=request.user)
        return success(TenantAdvanceSerializer(advance).data, message="Advance approved.")


class TenantAdvanceRejectView(APIView):
    def post(self, request, id):
        from .models import TenantAdvance
        from .services import reject_tenant_advance

        advance = generics.get_object_or_404(TenantAdvance, id=id)
        if advance.lease.landlord_id != request.user.id and request.user.role != 'admin':
            return Response({'success': False, 'error': {'message': 'Not authorized to reject this advance.'}}, status=403)
        reject_tenant_advance(advance, rejected_by=request.user, reason=request.data.get('reason', ''))
        return success(message="Advance rejected.")


class ServiceProviderInvoiceListCreateView(generics.ListCreateAPIView):
    from .serializers import ServiceProviderInvoiceSerializer
    serializer_class = ServiceProviderInvoiceSerializer

    def get_queryset(self):
        from .models import ServiceProviderInvoice
        user = self.request.user
        if user.role == 'admin':
            return ServiceProviderInvoice.objects.all().order_by('-created_at')
        if user.role == 'service_provider':
            return ServiceProviderInvoice.objects.filter(provider=user).order_by('-created_at')
        return ServiceProviderInvoice.objects.filter(job__posted_by=user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        from .serializers import SubmitServiceProviderInvoiceSerializer, ServiceProviderInvoiceSerializer
        from .services import submit_service_provider_invoice
        from apps.services.models import ServiceJob

        serializer = SubmitServiceProviderInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        job = generics.get_object_or_404(ServiceJob, id=data['job_id'], assigned_provider=request.user)
        invoice = submit_service_provider_invoice(
            job=job, provider=request.user, amount=data['amount'], description=data.get('description', ''),
            attachment=request.FILES.get('attachment'),
        )
        return success(
            ServiceProviderInvoiceSerializer(invoice).data, message="Invoice submitted.", status_code=status.HTTP_201_CREATED,
        )


class ServiceProviderInvoiceApproveView(APIView):
    def post(self, request, id):
        from .models import ServiceProviderInvoice
        from .services import approve_service_provider_invoice
        from .serializers import ServiceProviderInvoiceSerializer

        invoice = generics.get_object_or_404(ServiceProviderInvoice, id=id)
        if invoice.job.posted_by_id != request.user.id and request.user.role != 'admin':
            return Response({'success': False, 'error': {'message': 'Not authorized to approve this invoice.'}}, status=403)
        invoice = approve_service_provider_invoice(invoice, reviewed_by=request.user, notes=request.data.get('notes', ''))
        return success(ServiceProviderInvoiceSerializer(invoice).data, message="Invoice approved.")


class ServiceProviderInvoiceRejectView(APIView):
    def post(self, request, id):
        from .models import ServiceProviderInvoice
        from .services import reject_service_provider_invoice

        invoice = generics.get_object_or_404(ServiceProviderInvoice, id=id)
        if invoice.job.posted_by_id != request.user.id and request.user.role != 'admin':
            return Response({'success': False, 'error': {'message': 'Not authorized to reject this invoice.'}}, status=403)
        reject_service_provider_invoice(invoice, reviewed_by=request.user, notes=request.data.get('notes', ''))
        return success(message="Invoice rejected.")


class ServiceProviderInvoicePayView(APIView):
    def post(self, request, id):
        from .models import ServiceProviderInvoice
        from .services import pay_service_provider_invoice
        from .serializers import PayoutSerializer

        invoice = generics.get_object_or_404(ServiceProviderInvoice, id=id)
        if invoice.job.posted_by_id != request.user.id and request.user.role != 'admin':
            return Response({'success': False, 'error': {'message': 'Not authorized to pay this invoice.'}}, status=403)
        try:
            payout = pay_service_provider_invoice(invoice, initiated_by=request.user)
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)
        return success(PayoutSerializer(payout).data, message="Payout initiated.", status_code=status.HTTP_201_CREATED)


class ReceiptVerifyView(APIView):
    """
    Public receipt check: confirms a payment reference is a real, completed FRIDAH payment.
    Returns only non-sensitive facts (no payer name/phone, no property address).
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_throttles(self):
        from apps.users.throttling import SafeAnonRateThrottle
        return [SafeAnonRateThrottle()]

    def get(self, request):
        ref = (request.query_params.get('reference') or '').strip()
        if len(ref) < 6:
            return Response({'success': False, 'error': {'message': 'A payment reference is required.'}}, status=400)
        payment = Payment.objects.filter(reference__iexact=ref).first()
        if payment is None or payment.status != Payment.Status.COMPLETED:
            return Response({'success': True, 'data': {'valid': False}})
        return Response({'success': True, 'data': {
            'valid': True, 'reference': payment.reference, 'amount': payment.amount, 'currency': 'KES',
            'paid_at': payment.completed_at, 'method': payment.method,
        }})


class ResolveDisputedPaymentView(APIView):
    """POST {action: confirm|void, reason} - administrators only."""
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import resolve_disputed_payment
        payment = get_object_or_404(Payment, id=id)
        try:
            payment = resolve_disputed_payment(payment, request.user, request.data.get('action'), request.data.get('reason', ''))
        except DjangoValidationError as e:
            return Response({'success': False, 'error': {'message': ' '.join(e.messages)}}, status=400)
        return success({'status': payment.status}, 'Dispute resolved.')


# --------------------------------------------------------------------------- refunds & reversals
def _bad(message, code=400):
    return Response({'success': False, 'error': {'message': message}}, status=code)


class RefundRequestView(APIView):
    """POST {amount, reason, kind?: refund|reversal} - payer, recipient or administrator."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from . import refunds
        from .serializers import RefundSerializer
        payment = get_object_or_404(Payment, id=id)
        try:
            refund = refunds.request_refund(
                payment, request.user, request.data.get('amount') or 0, request.data.get('reason', ''),
                kind=request.data.get('kind', 'refund'),
            )
        except DjangoValidationError as e:
            return _bad(' '.join(e.messages))
        except ArithmeticError:
            return _bad('Invalid amount.')
        return Response({'success': True, 'data': RefundSerializer(refund, context={'request': request}).data}, status=201)


def _refunds_visible_to(user):
    """Admins see every request; everyone else sees requests they made, paid, or would be debited for."""
    from django.db.models import Q
    qs = Refund.objects.select_related('payment', 'requested_by', 'decided_by')
    if user.role == 'admin' or user.is_staff:
        return qs
    return qs.filter(
        Q(requested_by=user) | Q(payment__payer=user)
        | Q(payment__invoice__lease__landlord=user) | Q(payment__booking__host=user)
    ).distinct()


class RefundListView(generics.ListAPIView):
    """Admins see every request; everyone else sees requests they made, paid, or would be debited for."""
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'kind']

    def get_serializer_class(self):
        from .serializers import RefundSerializer
        return RefundSerializer

    def get_queryset(self):
        return _refunds_visible_to(self.request.user)


class RefundActionView(APIView):
    """POST /refunds/<id>/<action>/ where action is approve | reject | cancel | mark-paid."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, action):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from . import refunds
        from .serializers import RefundSerializer
        refund = get_object_or_404(_refunds_visible_to(request.user), id=id)
        try:
            if action == 'approve':
                allow_neg = str(request.data.get('allow_negative_balance', '')).lower() in ('1', 'true', 'yes')
                refund = refunds.approve_refund(refund, request.user, request.data.get('comment', ''), allow_negative_balance=allow_neg)
            elif action == 'reject':
                refund = refunds.reject_refund(refund, request.user, request.data.get('comment', ''))
            elif action == 'cancel':
                refund = refunds.cancel_refund(refund, request.user)
            elif action == 'mark-paid':
                refund = refunds.mark_refund_paid(refund, request.user, request.data.get('reference', ''))
            elif action == 'pay-out':
                refunds.initiate_refund_payout(refund, request.user, request.data.get('phone_number'))
            else:
                return _bad('Unknown action.', 404)
        except DjangoValidationError as e:
            return _bad(' '.join(e.messages))
        refund.refresh_from_db()
        return Response({'success': True, 'data': RefundSerializer(refund, context={'request': request}).data})


# --------------------------------------------------------------------------- reconciliation (admin)
class ReconciliationRunListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        from .serializers import ReconciliationRunSerializer
        return ReconciliationRunSerializer

    def get_queryset(self):
        return ReconciliationRun.objects.all()


class ReconciliationRunDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, id):
        from .serializers import ReconciliationRunSerializer, ReconciliationItemSerializer
        run = get_object_or_404(ReconciliationRun, id=id)
        only_open = request.query_params.get('open') in ('1', 'true')
        items = run.items.select_related('payment')
        if only_open:
            items = items.filter(resolved=False)
        return Response({'success': True, 'data': {
            'run': ReconciliationRunSerializer(run).data, 'items': ReconciliationItemSerializer(items, many=True).data,
        }})


def _period(request, default_days=1):
    from datetime import date, timedelta
    try:
        end = date.fromisoformat(request.data.get('period_end') or request.query_params.get('end') or '') 
    except ValueError:
        end = timezone.localdate() - timedelta(days=1)
    try:
        start = date.fromisoformat(request.data.get('period_start') or request.query_params.get('start') or '')
    except ValueError:
        start = end - timedelta(days=default_days - 1)
    return start, end


class RunInternalReconciliationView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        from .reconciliation import run_internal_checks
        from .serializers import ReconciliationRunSerializer
        start, end = _period(request, default_days=1)
        run = run_internal_checks(start, end, created_by=request.user)
        return Response({'success': True, 'data': ReconciliationRunSerializer(run).data}, status=201)


class UploadStatementView(APIView):
    """POST multipart: file (Safaricom statement CSV), period_start, period_end."""
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .reconciliation import parse_statement_csv, reconcile_statement
        from .serializers import ReconciliationRunSerializer
        f = request.FILES.get('file')
        if f is None:
            return _bad('Attach the statement as a CSV file.')
        if f.size > 5 * 1024 * 1024:
            return _bad('The statement file is too large (limit 5 MB).')
        start, end = _period(request, default_days=31)
        try:
            rows, skipped = parse_statement_csv(f.read())
        except DjangoValidationError as e:
            return _bad(' '.join(e.messages))
        if not rows:
            return _bad('No payment lines were found in this file.')
        run = reconcile_statement(rows, start, end, created_by=request.user, file_name=f.name)
        data = ReconciliationRunSerializer(run).data
        data['skipped_lines'] = skipped
        return Response({'success': True, 'data': data}, status=201)


class ResolveReconciliationItemView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .reconciliation import resolve_item
        from .serializers import ReconciliationItemSerializer
        item = get_object_or_404(ReconciliationItem, id=id)
        try:
            item = resolve_item(item, request.user, request.data.get('note', ''))
        except DjangoValidationError as e:
            return _bad(' '.join(e.messages))
        return Response({'success': True, 'data': ReconciliationItemSerializer(item).data})


class SettlementSummaryView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        from datetime import timedelta
        from .reconciliation import settlement_summary
        end = timezone.localdate()
        start = end - timedelta(days=29)
        try:
            from datetime import date
            if request.query_params.get('start'):
                start = date.fromisoformat(request.query_params['start'])
            if request.query_params.get('end'):
                end = date.fromisoformat(request.query_params['end'])
        except ValueError:
            return _bad('Dates must be YYYY-MM-DD.')
        return Response({'success': True, 'data': settlement_summary(start, end)})


class RefundPolicyView(APIView):
    """GET: any signed-in user (the request form shows the approval limit). PUT: administrators only."""

    def get_permissions(self):
        return [IsAdminRole()] if self.request.method == 'PUT' else [permissions.IsAuthenticated()]

    def get(self, request):
        from .refunds import current_policy
        return Response({'success': True, 'data': current_policy()})

    def put(self, request):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .refunds import update_policy
        try:
            data = update_policy(request.user, request.data.get('admin_approval_above'), request.data.get('window_days'))
        except DjangoValidationError as e:
            return _bad(' '.join(e.messages))
        return Response({'success': True, 'data': data})
