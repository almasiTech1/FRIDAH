# Google Maps setup

## What is in the app
- **Public Properties and Hotels pages:** map view with clustered pins, "Near me", distance sorting, "Directions" in each pin's pop-up.
- **House and hotel pages:** a "Location" section with a map, **Get directions** and **Open in Google Maps**. With no key or no pin it still shows the address and working Google Maps links.
- **Landlord, hotel and admin forms:** Google address search (Kenya only) that fills in county and town and drops a pin, plus a **map where you click or drag the pin** to the exact entrance, and "Use my location".
- **Backend:** coordinates from Google are rounded to 6 decimals (about 10 cm) and range-checked; before, saving a pinned address failed with "no more than 9 digits" and a latitude of 500 was accepted.

## Get a key (about 10 minutes)
1. Open the Google Cloud console, create a project, and attach a billing account. Maps Platform requires billing even though it has free monthly usage; check the current pricing page and **set a budget alert**.
2. In *APIs & Services > Library* enable **both**:
   - **Maps JavaScript API**
   - **Places API (New)**. Google stopped offering the older "Places API" widget to new projects in March 2025; this app uses the new one.
3. *APIs & Services > Credentials > Create credentials > API key*, then **restrict it**:
   - *Application restrictions:* Websites (HTTP referrers), for example `https://fridah.co.ke/*`, `https://www.fridah.co.ke/*` and `http://localhost:5173/*` while developing.
   - *API restrictions:* only Maps JavaScript API and Places API (New).
   A key in a web app can be read by anyone who views the page; these restrictions are what stop others using it.
4. Put it in `fridah-web/.env`: `VITE_GOOGLE_MAPS_API_KEY=your-key`, then rebuild (`npx vite build`).

The generated security headers already allow Google Maps. If you change them, keep `*.googleapis.com`, `*.gstatic.com` and `*.google.com`.

## If something does not work
Open the browser console (F12). Google names the problem:
| Message | Meaning |
|---|---|
| `ApiNotActivatedMapError` | Maps JavaScript API is not enabled for the project |
| `RefererNotAllowedMapError` | The page address is not in the key's allowed referrers |
| `BillingNotEnabledMapError` | No billing account on the project |
| `InvalidKeyMapError` | Key typed wrongly or deleted |
- The address box turns into a plain text box with "Address search is unavailable right now" when **Places API (New)** is not enabled or not in the key's API restrictions. The pin map still works.
- Not covered: the mobile app has its own map code and was not changed.
