// Ai generated
// My bookings page: lists the guest's bookings and lets them cancel one.
// Cancelling asks the backend (POST /bookings/{id}/cancel), which refunds the card in full and frees the parking spot.

// When the page is opened from localhost it talks to the same server; anywhere else it uses the Render backend.
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const TOKEN_KEY = "gdp-token";
const list = document.getElementById("list");
const note = document.getElementById("note");
const money = (n) => "$" + Number(n).toFixed(2).replace(/\.00$/, "");

// Makes an HTML element, sets its properties, and adds children. textContent is used instead of innerHTML
// so text that came from the database can never run as code.
function el(tag, props = {}, ...kids) {
  const node = Object.assign(document.createElement(tag), props);
  kids.flat().forEach((k) => node.append(k));
  return node;
}

// Shows a message at the top of the page. isError turns it red.
function say(text, isError) {
  note.textContent = text;
  note.className = isError ? "status-error" : "muted";
}

// Asks the backend for this guest's bookings and draws them. The optional message (like "Booking cancelled") is shown afterwards.
async function load(message) {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return location.replace("/login");           // bookings are private, so sign in first
  try {
    const res = await fetch(`${API}/bookings`, { headers: { Authorization: "Bearer " + token } });
    if (res.status === 401) { localStorage.removeItem(TOKEN_KEY); return location.replace("/login"); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Couldn’t load your bookings.");
    render(data);
    if (message) say(message, false);
  } catch (err) {
    say(err.message, true);
  }
}

// Draws one card per booking, or a friendly message if there are none.
function render(bookings) {
  list.replaceChildren();
  if (!bookings.length) {
    say("You have no bookings yet. Find a spot from the All events page.", false);
    return;
  }
  say(bookings.length + (bookings.length === 1 ? " booking" : " bookings") + ", newest first", false);
  bookings.forEach((b) => {
    // The bottom part of each card depends on the booking: cancelled, still cancellable, or too late to cancel.
    let status;
    if (b.cancelled) {
      status = el("span", { className: "flag", textContent: "Cancelled · refunded" });
    } else if (b.can_cancel) {
      status = el("button", { className: "btn btn-danger cancel-btn", textContent: "Cancel booking" });
      status.addEventListener("click", () => cancel(b, status));
    } else {
      status = el("p", { className: "spot-line muted", textContent: "This booking can’t be cancelled any more because the event is too close." });
    }
    list.append(el("li", { className: "spot" + (b.cancelled ? " cancelled" : "") },
      el("div", { className: "spot-top" },
        el("strong", { textContent: b.event }),
        el("span", { className: "spot-price", textContent: money(b.amount) })),
      el("p", { className: "spot-line muted", textContent: `${b.venue} · ${b.date}` }),
      el("p", { className: "spot-line", textContent: b.address }),
      el("p", { className: "spot-line muted", textContent: `${b.start}–${b.end} · Plate ${b.plate}` }),
      status));
  });
}

// Runs when a guest clicks "Cancel booking". It asks "are you sure?" first, because a cancellation can't be undone.
async function cancel(b, button) {
  if (!confirm(`Cancel your booking at ${b.address}? You will be refunded ${money(b.amount)}.`)) return;
  button.disabled = true;                                   // stops a second click while we wait
  say("Cancelling and refunding…", false);
  try {
    const res = await fetch(`${API}/bookings/${encodeURIComponent(b.id)}/cancel`, {
      method: "POST", headers: { Authorization: "Bearer " + localStorage.getItem(TOKEN_KEY) },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) { localStorage.removeItem(TOKEN_KEY); return location.replace("/login"); }
    if (!res.ok) {
      // Show the reason the server gave, such as "the event is too close" or "refund couldn't be processed right now".
      say(typeof data.detail === "string" ? data.detail : "Couldn’t cancel this booking. Try again.", true);
      button.disabled = false;
      return;
    }
    // Success: reload the list so the card shows as cancelled. Banks usually take a few days to show the refund.
    load(`Booking cancelled. ${money(b.amount)} is on its way back to your card (banks usually take 5 to 10 days to show it).`);
  } catch (err) {
    say("Couldn’t reach the server. Your booking has not been changed. Try again.", true);
    button.disabled = false;
  }
}

load();
