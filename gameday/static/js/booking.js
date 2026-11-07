// Ai generated
// Booking page (tasks bpage and bui). Shows the chosen spot, takes the hours, licence plate and card, sends them to the
// backend (POST /bookings), then either goes to the confirmation page (success) or shows a clear message (failure).
// The spot id comes from the address, e.g. booking.html?listing=l1a2b3c4 (the "Book this spot" buttons on the browse page put it there).

// When the page is opened from localhost it talks to the same server; anywhere else it uses the Render backend.
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const TOKEN_KEY = "gdp-token";
const listingId = new URLSearchParams(location.search).get("listing");

const pageNote = document.getElementById("page-note");
const form = document.getElementById("booking-form");
const formMsg = document.getElementById("form-msg");
const payBtn = document.getElementById("pay-btn");
const money = (n) => "$" + Number(n).toFixed(2).replace(/\.00$/, "");
// "2026-11-15T15:00:00+00:00" -> "09:00" in Chicago time, the format the time boxes need.
const hhmm = (iso) => new Date(iso).toLocaleTimeString("en-GB",
  { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "America/Chicago" });

let stripe, card;   // Stripe's tools, created once the page has loaded

// A random code that identifies THIS checkout attempt. The backend gives it to Stripe as an "idempotency key":
// if the same code arrives twice (a double click, or a retry after a bad connection) the guest is charged only once.
let requestId = crypto.randomUUID();

// Shows a message under the form. isError turns it red.
function say(text, isError) {
  formMsg.textContent = text;
  formMsg.className = "form-msg" + (isError ? " status-error" : "");
}

// Loads the spot and Stripe's settings, then shows the summary and the form.
async function load() {
  // Only signed-in guests can book. Everyone else is sent to the login page.
  if (!localStorage.getItem(TOKEN_KEY)) return location.replace("/login");
  if (!listingId) {
    pageNote.textContent = "Go back to All events and choose a parking spot to book.";
    return;
  }
  try {
    // Ask for the spot and for the Stripe key at the same time.
    const [res, cfgRes] = await Promise.all([
      fetch(`${API}/listings/${encodeURIComponent(listingId)}`),
      fetch(`${API}/booking/config`),
    ]);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Couldn’t load this parking spot.");
    const cfg = await cfgRes.json().catch(() => ({}));
    if (!cfg.publishable_key) throw new Error("Payments aren’t set up yet. Please try again later.");

    // Fill in the summary. textContent (not innerHTML) is used so text from the database can never run as code.
    const { event: ev, listing: l } = data;
    document.getElementById("s-event").textContent = ev.name;
    document.getElementById("s-venue").textContent = ev.venue;
    document.getElementById("s-address").textContent = l.address;
    const open = hhmm(l.start_at), close = hhmm(l.end_at);
    document.getElementById("s-walk").textContent = `${l.walk} min walk from the venue · Available ${open}–${close}`;
    document.getElementById("s-price").textContent = money(l.price);

    // The time boxes start on the host's full window and can't go outside it.
    for (const [id, value] of [["start", open], ["end", close]]) {
      const box = document.getElementById(id);
      box.min = open; box.max = close; box.value = value;
    }
    form.dataset.open = open; form.dataset.close = close;

    // Start Stripe's secure card form inside the #card-element box.
    stripe = Stripe(cfg.publishable_key);
    card = stripe.elements().create("card");
    card.mount("#card-element");

    pageNote.hidden = true;
    document.getElementById("summary").hidden = false;
    form.hidden = false;
  } catch (err) {
    pageNote.textContent = err.message;
    pageNote.className = "status-error";
  }
}

// Runs when the guest clicks "Pay and book".
form.addEventListener("submit", async (e) => {
  e.preventDefault();   // stops the page from reloading
  form.querySelectorAll("input").forEach((i) => i.classList.remove("err"));
  say("", false);

  const start = form.start.value, end = form.end.value, plate = form.plate.value.trim();

  // Checks we can do in the browser, before any server call. (The backend checks everything again.)
  if (!start || !end || start >= end || start < form.dataset.open || end > form.dataset.close) {
    form.start.classList.add("err"); form.end.classList.add("err");
    return say(`Choose hours between ${form.dataset.open} and ${form.dataset.close}, with the arrival before the leave time.`, true);
  }
  if (!plate) {
    form.plate.classList.add("err");
    return say("Enter your licence plate.", true);
  }

  payBtn.disabled = true;   // stops a second click from starting a second payment
  say("Processing your payment…", false);
  try {
    // Ask Stripe to turn the card details into a one-time token. The card number never touches our server.
    const { paymentMethod, error } = await stripe.createPaymentMethod({ type: "card", card });
    if (error) return say(error.message, true);   // e.g. "Your card number is incomplete."

    // Send the booking to our backend. The token proves who is booking.
    const res = await fetch(`${API}/bookings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + localStorage.getItem(TOKEN_KEY) },
      body: JSON.stringify({ listing_id: listingId, start, end, plate, payment_method_id: paymentMethod.id, request_id: requestId }),
    });
    const data = await res.json().catch(() => ({}));

    // Success: go to the confirmation screen.
    if (res.ok) return (window.location.href = `/static/booking_confirmed.html?id=${encodeURIComponent(data.id)}`);

    // Signed out or the login expired: send them to log in again.
    if (res.status === 401) { localStorage.removeItem(TOKEN_KEY); return location.replace("/login"); }

    // Failure: show the reason the server gave. A string means a clear message we wrote; anything else is a format problem.
    say(typeof data.detail === "string" ? data.detail : "Check your hours and licence plate, then try again.", true);

    // 402 (card declined), 409 (spot taken) and 422 (bad details) all mean "no money was taken". The next try is a NEW
    // checkout, so it gets a new code. For other errors (such as 503) we KEEP the code, so retrying can't charge twice.
    if ([402, 409, 422].includes(res.status)) requestId = crypto.randomUUID();
  } catch (err) {
    // The request failed on the way (no internet, server down). We can't tell if the payment went through, so we keep the
    // same code: pressing "Pay and book" again is safe and will not charge twice.
    say("We couldn’t confirm your booking because the connection failed. Press “Pay and book” again. You won’t be charged twice.", true);
  } finally {
    payBtn.disabled = false;
  }
});

load();
