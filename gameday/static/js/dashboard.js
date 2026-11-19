// Ai generated
// Dashboard page (tasks dashui and dashconn). Asks the backend for the signed-in guest's bookings (GET /dashboard/bookings),
// then shows them in two sections: "Upcoming bookings" and "Past bookings".
// If there are no bookings at all, it shows a prompt with a button to browse upcoming events instead.
// Old or damaged bookings can be missing information (a host name, a receipt, a date...). Everything below is written so a
// missing piece shows a friendly fallback and NEVER crashes the page: values are read with ?. and ??, and each booking card
// is built inside its own try/catch, so one bad booking can't stop the others from showing.

// When the page is opened from localhost it talks to the same server; anywhere else it uses the Render backend.
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const TOKEN_KEY = "gdp-token";

const note = document.getElementById("note");
const emptyBox = document.getElementById("empty-box");
const sections = document.getElementById("sections");
const upcomingList = document.getElementById("upcoming-list");
const pastList = document.getElementById("past-list");
const upcomingEmpty = document.getElementById("upcoming-empty");
const pastEmpty = document.getElementById("past-empty");

const money = (n) => "$" + Number(n ?? 0).toFixed(2).replace(/\.00$/, "");

// Shows a date or time in the STADIUM'S own time zone. If the value is missing or damaged (or the time zone name is wrong),
// it shows the fallback text instead of crashing.
function show(iso, tz, options, fallback) {
  try {
    if (!iso) return fallback;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return fallback;
    return d.toLocaleString([], { ...options, timeZone: tz || undefined });
  } catch (err) {
    return fallback;
  }
}
const clock = (iso, tz) => show(iso, tz, { hour: "numeric", minute: "2-digit" }, "time not available");
const day = (iso, tz) => show(iso, tz, { weekday: "short", month: "short", day: "numeric" }, "date not available");

// Makes an HTML element with optional class and text. textContent is used (never innerHTML)
// so text that came from the database can never run as code.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// Shows a message at the top of the page. isError turns it red.
function say(text, isError) {
  note.textContent = text;
  note.className = isError ? "status-error" : "muted";
}

// Sends the guest to the login page (used when they are signed out or their login has expired).
function signedOut() {
  localStorage.removeItem(TOKEN_KEY);
  location.replace("/login");
}

// Task dashconn: asks the backend for the bookings and draws the page. The optional message (like "Booking cancelled")
// is shown afterwards. Who the bookings belong to is decided by the server from the login token, never by this page.
async function load(message) {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return location.replace("/login");           // bookings are private, so sign in first
  try {
    const res = await fetch(`${API}/dashboard/bookings`, { headers: { Authorization: "Bearer " + token } });
    if (res.status === 401) return signedOut();
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Couldn’t load your bookings.");
    render(data);
    if (message) say(message, false);
  } catch (err) {
    say(err.message, true);
  }
}

// Decides what to show. Both lists empty = the "browse events" prompt. Otherwise the two sections, and a short
// friendly line inside whichever section happens to be empty.
function render(data) {
  const upcoming = Array.isArray(data?.upcoming) ? data.upcoming : [];
  const past = Array.isArray(data?.past) ? data.past : [];
  const nothing = !upcoming.length && !past.length;

  emptyBox.hidden = !nothing;
  sections.hidden = nothing;
  upcomingEmpty.hidden = upcoming.length > 0;
  pastEmpty.hidden = past.length > 0;
  fill(upcomingList, upcoming);
  fill(pastList, past);
  say(nothing ? "" : `${upcoming.length} upcoming · ${past.length} past`, false);
}

// Draws one card per booking. Each card is built inside its own try/catch, so a damaged booking shows a short
// "can't be shown" card and every other booking still appears.
function fill(listEl, bookings) {
  listEl.replaceChildren();
  bookings.forEach((b) => {
    try {
      listEl.append(card(b));
    } catch (err) {
      console.error("Couldn't show a booking:", err);
      listEl.append(el("li", "spot", "This booking can’t be shown right now."));
    }
  });
}

// Builds the card for ONE booking: the event, the spot details, the host's contact details and the receipt.
function card(b) {
  const tz = b?.timezone;
  const host = b?.host ?? {};
  const receipt = b?.receipt ?? {};
  const status = b?.status ?? "confirmed";

  // A short label for bookings that are not active any more.
  let label = null;
  if (status === "canceled") label = "Cancelled · refunded";
  else if (status === "refunded") label = "Refunded · the host cancelled this spot";

  const li = el("li", "spot" + (label ? " cancelled" : ""));

  // Top line: event name on the left, price on the right.
  const top = el("div", "spot-top");
  top.append(el("strong", "", b?.event ?? "Event no longer available"), el("span", "spot-price", money(receipt?.amount)));
  li.append(top);
  li.append(el("p", "spot-line muted", `${b?.venue ?? ""} · ${day(b?.start_at, tz)}, ${clock(b?.start_at, tz)} – ${clock(b?.end_at, tz)}`));
  if (label) li.append(el("span", "flag", label));

  // Spot details.
  li.append(el("p", "spot-line", b?.address ?? "Spot no longer available"));
  const extras = [];
  if (b?.walk) extras.push(`${b.walk} min walk from the venue`);
  if (b?.plate) extras.push(`Plate ${b.plate}`);
  if (extras.length) li.append(el("p", "spot-line muted", extras.join(" · ")));
  if (b?.stacked) li.append(el("span", "flag", "Stacked parking"));
  if (b?.security) li.append(el("p", "spot-line", "Security: " + b.security));

  // Host contact details. A missing phone or email is simply left out.
  const hostLine = el("p", "spot-line host-line");
  hostLine.append(el("strong", "", "Host: "), host?.name ?? "Host details unavailable");
  if (host?.phone) {
    const phone = el("a", "", host.phone);
    phone.href = "tel:" + String(host.phone).replace(/[^\d+]/g, "");
    hostLine.append(" · ", phone);
  }
  if (host?.email) {
    const mail = el("a", "", host.email);
    mail.href = "mailto:" + host.email;
    hostLine.append(" · ", mail);
  }
  li.append(hostLine);

  li.append(receiptBox(b, receipt, tz));

  // The Cancel button, only while the rule still allows it (the server decides and sends can_cancel).
  if (b?.can_cancel) {
    const btn = el("button", "btn btn-danger cancel-btn", "Cancel booking");
    btn.addEventListener("click", () => cancel(b, btn));
    li.append(btn);
  }
  return li;
}

// The receipt: the details we saved when the guest paid, plus a button that opens Stripe's official receipt page.
// Details that are missing are left out rather than shown as "undefined".
function receiptBox(b, receipt, tz) {
  const box = el("details", "receipt");
  box.append(el("summary", "", "Receipt"));
  box.append(el("p", "spot-line", "Receipt number: " + (receipt?.number ?? b?.id ?? "not available")));
  box.append(el("p", "spot-line", "Amount paid: " + money(receipt?.amount)));
  if (receipt?.paid_at) box.append(el("p", "spot-line", "Paid on: " + day(receipt.paid_at, tz)));
  if (receipt?.payment_id) box.append(el("p", "spot-line muted", "Payment id: " + receipt.payment_id));

  const msg = el("p", "spot-line");
  const btn = el("button", "btn btn-accent", "View Stripe receipt");
  btn.addEventListener("click", () => openStripeReceipt(b?.id, btn, msg));
  box.append(btn, msg);
  return box;
}

// Asks the backend for the link to Stripe's receipt page for one booking, and opens it in a new tab.
async function openStripeReceipt(id, button, msg) {
  button.disabled = true;                                   // stops a second click while we wait
  msg.textContent = "Getting your receipt…";
  try {
    const res = await fetch(`${API}/bookings/${encodeURIComponent(id)}/receipt`, {
      headers: { Authorization: "Bearer " + localStorage.getItem(TOKEN_KEY) },
    });
    if (res.status === 401) return signedOut();
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.url) {
      msg.textContent = typeof data.detail === "string" ? data.detail : "The Stripe receipt isn’t available right now.";
      return;
    }
    msg.textContent = "";
    if (!window.open(data.url, "_blank", "noopener")) location.href = data.url;   // if a pop-up blocker stops the new tab, open it here
  } catch (err) {
    msg.textContent = "Couldn’t reach the server. Try again.";
  } finally {
    button.disabled = false;
  }
}

// Runs when a guest clicks "Cancel booking". It asks "are you sure?" first, because a cancellation can't be undone.
async function cancel(b, button) {
  if (!confirm(`Cancel your booking at ${b?.address ?? "this spot"}? You will be refunded ${money(b?.receipt?.amount)}.`)) return;
  button.disabled = true;                                   // stops a second click while we wait
  say("Cancelling and refunding…", false);
  try {
    const res = await fetch(`${API}/bookings/${encodeURIComponent(b.id)}/cancel`, {
      method: "POST", headers: { Authorization: "Bearer " + localStorage.getItem(TOKEN_KEY) },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) return signedOut();
    if (!res.ok) {
      // Show the reason the server gave, such as "the event is too close" or "refund couldn't be processed right now".
      say(typeof data.detail === "string" ? data.detail : "Couldn’t cancel this booking. Try again.", true);
      button.disabled = false;
      return;
    }
    // Success: reload the dashboard so the booking moves to "Past bookings" marked as cancelled.
    load(`Booking cancelled. ${money(b?.receipt?.amount)} is on its way back to your card (banks usually take 5 to 10 days to show it).`);
  } catch (err) {
    say("Couldn’t reach the server. Your booking has not been changed. Try again.", true);
    button.disabled = false;
  }
}

load();