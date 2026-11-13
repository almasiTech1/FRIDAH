import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { navigationRef } from './navigationRef'
import { createStackNavigator } from '@react-navigation/stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Text, View } from 'react-native'

// Auth
import { LoginScreen } from '@/screens/auth/LoginScreen'
import { RegisterScreen } from '@/screens/auth/RegisterScreen'

// Tenant
import { TenantDashboardScreen } from '@/screens/tenant/DashboardScreen'
import { TenantInvoicesScreen } from '@/screens/tenant/InvoicesScreen'
import { TenantMaintenanceScreen } from '@/screens/tenant/MaintenanceScreen'
import { TenantPropertiesScreen } from '@/screens/tenant/PropertiesScreen'
import { PropertyDetailScreen } from '@/screens/tenant/PropertyDetailScreen'
import { MyApplicationsScreen } from '@/screens/tenant/MyApplicationsScreen'
import { BrowseStaysScreen } from '@/screens/tenant/BrowseStaysScreen'
import { HotelDetailScreen } from '@/screens/tenant/HotelDetailScreen'
import { MyBookingsScreen } from '@/screens/tenant/MyBookingsScreen'
import { BookingConfirmationScreen } from '@/screens/tenant/BookingConfirmationScreen'
import { TenantNotificationsScreen } from '@/screens/tenant/NotificationsScreen'
import { TenantProfileScreen } from '@/screens/tenant/ProfileScreen'
import { TenantMessagesScreen } from '@/screens/tenant/MessagesScreen'

// Landlord
import { LandlordDashboardScreen } from '@/screens/landlord/DashboardScreen'
import { LandlordPropertiesScreen } from '@/screens/landlord/PropertiesScreen'
import { LandlordLeasesScreen } from '@/screens/landlord/LeasesScreen'
import { LandlordInvoicesScreen } from '@/screens/landlord/InvoicesScreen'
import { LandlordMaintenanceScreen } from '@/screens/landlord/MaintenanceScreen'
import { LandlordWalletScreen } from '@/screens/landlord/WalletScreen'
import { LandlordProfileScreen } from '@/screens/landlord/ProfileScreen'
import { LandlordApplicationsScreen } from '@/screens/landlord/ApplicationsScreen'
import { LandlordMessagesScreen } from '@/screens/landlord/MessagesScreen'
import { LandlordApprovalsScreen } from '@/screens/landlord/ApprovalsScreen'
import { LandlordTaxScreen } from '@/screens/landlord/TaxScreen'
import { LandlordAmenitiesScreen } from '@/screens/landlord/AmenitiesScreen'
import { AdminReviewQueueScreen } from '@/screens/admin/ReviewQueueScreen'
import { AdminAgenciesScreen } from '@/screens/admin/AgenciesScreen'
import { LandlordRefundsScreen } from '@/screens/landlord/RefundsScreen'
import { TenantRefundsScreen } from '@/screens/tenant/RefundsScreen'
import { AdminRefundsScreen } from '@/screens/admin/RefundsScreen'
import { AdminReconciliationScreen } from '@/screens/admin/ReconciliationScreen'
import { AdminProfileScreen } from '@/screens/admin/ProfileScreen'
import { ForceChangePasswordScreen } from '@/screens/auth/ForceChangePasswordScreen'

// Agency
import { AgencyDashboardScreen } from '@/screens/agency/DashboardScreen'
import { AgencyPropertiesScreen } from '@/screens/agency/PropertiesScreen'
import { AgencyStaffScreen } from '@/screens/agency/StaffScreen'
import { AgencyStatementsScreen } from '@/screens/agency/StatementsScreen'
import { AgencyMessagesScreen } from '@/screens/agency/MessagesScreen'
import { AgencyProfileScreen } from '@/screens/agency/ProfileScreen'
import { AgencyExpensesScreen } from '@/screens/agency/ExpensesScreen'
import { AgencyAuditLogScreen } from '@/screens/agency/AuditLogScreen'

// Admin
import { AdminDashboardScreen } from '@/screens/admin/DashboardScreen'
import { AdminUsersScreen } from '@/screens/admin/UsersScreen'
import { AdminKYCScreen } from '@/screens/admin/KYCScreen'
import { AdminPropertiesScreen } from '@/screens/admin/PropertiesScreen'
import { AdminPaybillScreen } from '@/screens/admin/PaybillScreen'
import { AdminBlacklistScreen } from '@/screens/admin/BlacklistScreen'

// Provider
import { ProviderDashboardScreen } from '@/screens/provider/DashboardScreen'
import { ProviderJobsScreen } from '@/screens/provider/JobsScreen'
import { ProviderMyJobsScreen } from '@/screens/provider/MyJobsScreen'
import { ProviderWalletScreen, ProviderProfileScreen } from '@/screens/provider/WalletProfileScreens'
import { ProviderMessagesScreen } from '@/screens/provider/MessagesScreen'

// Hotel
import {
  HotelDashboardScreen,
  HotelBookingsScreen,
  HotelWalletScreen,
  HotelProfileScreen,
} from '@/screens/hotel/HotelScreens'
import { HotelCalendarScreen } from '@/screens/hotel/CalendarScreen'
import { HotelMessagesScreen } from '@/screens/hotel/MessagesScreen'

import { getTheme, agencyTheme, colors, typography } from '@/theme'
import { useAuthStore } from '@/stores/authStore'
import type { Role } from '@/types'

const Stack = createStackNavigator()
const Tab = createBottomTabNavigator()

// ─── Tab icon helper ──────────────────────────────────────────────────────────
const TabIcon = ({ emoji, focused, color }: { emoji: string; focused: boolean; color: string }) => (
  <View style={{ alignItems: 'center' }}>
    <Text style={{ fontSize: focused ? 22 : 20, opacity: focused ? 1 : 0.5 }}>{emoji}</Text>
  </View>
)

const tabBarStyle = (accentColor: string) => ({
  tabBarStyle: {
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
    height: 62,
    paddingBottom: 8,
    paddingTop: 6,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
  },
  tabBarActiveTintColor: accentColor,
  tabBarInactiveTintColor: colors.gray400,
  tabBarLabelStyle: { fontSize: 10, fontWeight: '600' as const },
  headerShown: false,
})

// ─── Auth Stack ───────────────────────────────────────────────────────────────
const AuthStack = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="Login" component={LoginScreen} />
    <Stack.Screen name="Register" component={RegisterScreen} />
  </Stack.Navigator>
)

// ─── Tenant Tabs ──────────────────────────────────────────────────────────────
const TenantTabsInner = () => {
  const theme = getTheme('tenant')
  return (
    <Tab.Navigator {...tabBarStyle(theme.primary)}>
      <Tab.Screen name="TenantDashboard" component={TenantDashboardScreen}
        options={{ title: 'Home', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantInvoices" component={TenantInvoicesScreen}
        options={{ title: 'Invoices', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🧾" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantMaintenance" component={TenantMaintenanceScreen}
        options={{ title: 'Maintenance', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🔧" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantMessages" component={TenantMessagesScreen}
        options={{ title: 'Messages', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💬" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantProperties" component={TenantPropertiesScreen}
        options={{ title: 'Browse', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏢" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantNotifications" component={TenantNotificationsScreen}
        options={{ title: 'Alerts', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🔔" focused={focused} color={color} /> }} />
      <Tab.Screen name="TenantProfile" component={TenantProfileScreen}
        options={{ title: 'Profile', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👤" focused={focused} color={color} /> }} />
    </Tab.Navigator>
  )
}

// Property/hotel detail, applications, stays browsing, and bookings are reached
// from the Dashboard's quick-action grid or by tapping into a list (not their
// own bottom tabs - the tab bar is already full), so TenantTabs is a stack
// wrapping the tab navigator plus these pushed detail screens, same pattern as
// AgencyTabs below.
const TenantTabs = () => {
  const theme = getTheme('tenant')
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="TenantTabsRoot" component={TenantTabsInner} />
      <Stack.Screen name="TenantRefunds" component={TenantRefundsScreen}
        options={{ headerShown: true, title: 'My Refunds', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="PropertyDetail" component={PropertyDetailScreen} />
      <Stack.Screen name="MyApplications" component={MyApplicationsScreen}
        options={{ headerShown: true, title: 'My Applications', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="BrowseStays" component={BrowseStaysScreen}
        options={{ headerShown: true, title: 'Hotels & BnBs', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="HotelDetail" component={HotelDetailScreen} />
      <Stack.Screen name="MyBookings" component={MyBookingsScreen}
        options={{ headerShown: true, title: 'My Bookings', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="BookingConfirmation" component={BookingConfirmationScreen} />
    </Stack.Navigator>
  )
}

// ─── Landlord Tabs ────────────────────────────────────────────────────────────
const LandlordTabsInner = () => {
  const theme = getTheme('landlord')
  return (
    <Tab.Navigator {...tabBarStyle(theme.primary)}>
      <Tab.Screen name="LandlordDashboard" component={LandlordDashboardScreen}
        options={{ title: 'Home', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordProperties" component={LandlordPropertiesScreen}
        options={{ title: 'Properties', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏢" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordLeases" component={LandlordLeasesScreen}
        options={{ title: 'Leases', tabBarIcon: ({ focused, color }) => <TabIcon emoji="📋" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordInvoices" component={LandlordInvoicesScreen}
        options={{ title: 'Invoices', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🧾" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordMaintenance" component={LandlordMaintenanceScreen}
        options={{ title: 'Repairs', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🔧" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordMessages" component={LandlordMessagesScreen}
        options={{ title: 'Messages', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💬" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordWallet" component={LandlordWalletScreen}
        options={{ title: 'Wallet', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💰" focused={focused} color={color} /> }} />
      <Tab.Screen name="LandlordAnalytics" component={LandlordDashboardScreen}
        options={{ title: 'Analytics', tabBarIcon: ({ focused, color }) => <TabIcon emoji="📊" focused={focused} color={color} /> }} />
    </Tab.Navigator>
  )
}

// LandlordTabs was already at 8 tabs (over the practical 6-tab limit noted on
// AgencyTabs below), so Profile and Applications - previously entirely missing
// on mobile for this role - are reached from the Dashboard's quick-action grid
// as pushed stack screens rather than adding yet more bottom tabs.
const LandlordTabs = () => {
  const theme = getTheme('landlord')
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="LandlordTabsRoot" component={LandlordTabsInner} />
      <Stack.Screen name="LandlordProfile" component={LandlordProfileScreen}
        options={{ headerShown: true, title: 'Profile', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="LandlordApplications" component={LandlordApplicationsScreen}
        options={{ headerShown: true, title: 'Rental Applications', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="LandlordRefunds" component={LandlordRefundsScreen}
        options={{ headerShown: true, title: 'Refunds', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="LandlordApprovals" component={LandlordApprovalsScreen}
        options={{ headerShown: true, title: 'Property Approvals', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="LandlordTax" component={LandlordTaxScreen}
        options={{ headerShown: true, title: 'Tax Records', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="LandlordAmenities" component={LandlordAmenitiesScreen}
        options={{ headerShown: true, title: 'Amenity Charges', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
    </Stack.Navigator>
  )
}

// ─── Agency Tabs ──────────────────────────────────────────────────────────────
const AgencyTabsInner = () => (
  <Tab.Navigator {...tabBarStyle(agencyTheme.primary)}>
    <Tab.Screen name="AgencyDashboard" component={AgencyDashboardScreen}
      options={{ title: 'Home', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏢" focused={focused} color={color} /> }} />
    <Tab.Screen name="AgencyProperties" component={AgencyPropertiesScreen}
      options={{ title: 'Properties', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
    <Tab.Screen name="AgencyStaff" component={AgencyStaffScreen}
      options={{ title: 'Staff', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👥" focused={focused} color={color} /> }} />
    <Tab.Screen name="AgencyStatements" component={AgencyStatementsScreen}
      options={{ title: 'Statements', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🧾" focused={focused} color={color} /> }} />
    <Tab.Screen name="AgencyMessages" component={AgencyMessagesScreen}
      options={{ title: 'Chat', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💬" focused={focused} color={color} /> }} />
    <Tab.Screen name="AgencyProfile" component={AgencyProfileScreen}
      options={{ title: 'Profile', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👤" focused={focused} color={color} /> }} />
  </Tab.Navigator>
)

// Expenses and the Audit Log are reached from the Dashboard's quick-action grid
// rather than living as their own bottom tabs (six tabs is already the practical
// limit for a comfortable bottom bar), so AgencyTabs is a small stack wrapping
// the tab navigator plus these two pushed detail screens.
const AgencyTabs = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="AgencyTabsRoot" component={AgencyTabsInner} />
    <Stack.Screen name="AgencyExpenses" component={AgencyExpensesScreen}
      options={{ headerShown: true, title: 'Expenses', headerStyle: { backgroundColor: agencyTheme.primary }, headerTintColor: colors.white }} />
    <Stack.Screen name="AgencyAuditLog" component={AgencyAuditLogScreen}
      options={{ headerShown: true, title: 'Audit Log', headerStyle: { backgroundColor: agencyTheme.primary }, headerTintColor: colors.white }} />
  </Stack.Navigator>
)

// ─── Admin Tabs ───────────────────────────────────────────────────────────────
const AdminTabsInner = () => {
  const theme = getTheme('admin')
  return (
    <Tab.Navigator {...tabBarStyle(theme.primary)}>
      <Tab.Screen name="AdminDashboard" component={AdminDashboardScreen}
        options={{ title: 'Dashboard', tabBarIcon: ({ focused, color }) => <TabIcon emoji="⚙️" focused={focused} color={color} /> }} />
      <Tab.Screen name="AdminUsers" component={AdminUsersScreen}
        options={{ title: 'Users', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👥" focused={focused} color={color} /> }} />
      <Tab.Screen name="AdminKYC" component={AdminKYCScreen}
        options={{ title: 'KYC', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🔒" focused={focused} color={color} /> }} />
      <Tab.Screen name="AdminProperties" component={AdminPropertiesScreen}
        options={{ title: 'Properties', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
      <Tab.Screen name="AdminPaybill" component={AdminPaybillScreen}
        options={{ title: 'Paybill', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🧾" focused={focused} color={color} /> }} />
      <Tab.Screen name="AdminBlacklist" component={AdminBlacklistScreen}
        options={{ title: 'Blacklist', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🚫" focused={focused} color={color} /> }} />
    </Tab.Navigator>
  )
}

// Admin tabs are at the practical limit, so the review queue is a pushed screen reached from Properties.
const AdminTabs = () => {
  const theme = getTheme('admin')
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="AdminTabsRoot" component={AdminTabsInner} />
      <Stack.Screen name="AdminReconciliation" component={AdminReconciliationScreen}
        options={{ headerShown: true, title: 'Reconciliation', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="AdminProfile" component={AdminProfileScreen}
        options={{ headerShown: true, title: 'My Account', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="AdminRefunds" component={AdminRefundsScreen}
        options={{ headerShown: true, title: 'Refunds & Reversals', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="AdminAgencies" component={AdminAgenciesScreen}
        options={{ headerShown: true, title: 'Agencies', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
      <Stack.Screen name="AdminReviewQueue" component={AdminReviewQueueScreen}
        options={{ headerShown: true, title: 'Property Review Queue', headerStyle: { backgroundColor: theme.primary }, headerTintColor: colors.white }} />
    </Stack.Navigator>
  )
}

// ─── Provider Tabs ────────────────────────────────────────────────────────────
const ProviderTabs = () => {
  const theme = getTheme('service_provider')
  return (
    <Tab.Navigator {...tabBarStyle(theme.primary)}>
      <Tab.Screen name="ProviderDashboard" component={ProviderDashboardScreen}
        options={{ title: 'Home', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
      <Tab.Screen name="ProviderJobs" component={ProviderJobsScreen}
        options={{ title: 'Open Jobs', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💼" focused={focused} color={color} /> }} />
      <Tab.Screen name="ProviderMyJobs" component={ProviderMyJobsScreen}
        options={{ title: 'My Jobs', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🔧" focused={focused} color={color} /> }} />
      <Tab.Screen name="ProviderMessages" component={ProviderMessagesScreen}
        options={{ title: 'Messages', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💬" focused={focused} color={color} /> }} />
      <Tab.Screen name="ProviderWallet" component={ProviderWalletScreen}
        options={{ title: 'Wallet', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💰" focused={focused} color={color} /> }} />
      <Tab.Screen name="ProviderProfile" component={ProviderProfileScreen}
        options={{ title: 'Profile', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👤" focused={focused} color={color} /> }} />
    </Tab.Navigator>
  )
}

// ─── Hotel Tabs ───────────────────────────────────────────────────────────────
const HotelTabs = () => {
  const theme = getTheme('hotel_owner')
  return (
    <Tab.Navigator {...tabBarStyle(theme.primary)}>
      <Tab.Screen name="HotelDashboard" component={HotelDashboardScreen}
        options={{ title: 'Home', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏨" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelListings" component={HotelDashboardScreen}
        options={{ title: 'Listings', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🏠" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelBookings" component={HotelBookingsScreen}
        options={{ title: 'Bookings', tabBarIcon: ({ focused, color }) => <TabIcon emoji="📅" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelCalendar" component={HotelCalendarScreen}
        options={{ title: 'Calendar', tabBarIcon: ({ focused, color }) => <TabIcon emoji="🗓️" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelMessages" component={HotelMessagesScreen}
        options={{ title: 'Messages', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💬" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelWallet" component={HotelWalletScreen}
        options={{ title: 'Wallet', tabBarIcon: ({ focused, color }) => <TabIcon emoji="💰" focused={focused} color={color} /> }} />
      <Tab.Screen name="HotelProfile" component={HotelProfileScreen}
        options={{ title: 'Profile', tabBarIcon: ({ focused, color }) => <TabIcon emoji="👤" focused={focused} color={color} /> }} />
    </Tab.Navigator>
  )
}

// ─── Root Navigator ───────────────────────────────────────────────────────────
const RootStack = createStackNavigator()

const roleTabsComponent: Record<Role, React.ComponentType<any>> = {
  tenant: TenantTabs,
  landlord: LandlordTabs,
  admin: AdminTabs,
  service_provider: ProviderTabs,
  hotel_owner: HotelTabs,
}

export const RootNavigator = () => {
  const user = useAuthStore((s) => s.user)
  const isAgencyStaff = useAuthStore((s) => s.isAgencyStaff())
  const RoleTabs = user ? (isAgencyStaff ? AgencyTabs : roleTabsComponent[user.role]) : null

  return (
    <NavigationContainer ref={navigationRef}>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {user?.must_change_password ? (
          // An admin-issued temporary password must be replaced before anything else is reachable.
          <RootStack.Screen name="ForceChangePassword" component={ForceChangePasswordScreen} />
        ) : RoleTabs ? (
          <RootStack.Group>
            <RootStack.Screen name="RoleTabs" component={RoleTabs} />
          </RootStack.Group>
        ) : (
          <RootStack.Screen name="Auth" component={AuthStack} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  )
}
