// Ai generated
// Browse page: shows the parking spots for the event that was clicked on the home page.
// The event id comes from the address, e.g. browse.html?event=v2 (the home page cards put it there).

// When the page is opened from localhost it talks to the same server; anywhere else it uses the Render backend.
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const eventId = new URLSearchParams(location.search).get("event");
const results = document.getElementById("results");
const NS = "http://www.w3.org/2000/svg";   // SVG shapes (the map) must be created in this namespace

// Small helpers --------------------------------------------------------------------------

// Makes an HTML element, sets its properties, and adds children. textContent is used instead of innerHTML
// so text that came from the database can never run as code.
function el(tag, props = {}, ...kids) {
  const node = Object.assign(document.createElement(tag), props);
  kids.flat().forEach((k) => node.append(k));
  return node;
}

// Same idea for SVG elements. attrs are set as attributes; text (optional) becomes the element's text.
function svg(tag, attrs = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const k in attrs) node.setAttribute(k, attrs[k]);
  if (text != null) node.textContent = text;
  return node;
}

const miles = (m) => (m / 1609.34).toFixed(2) + " mi";
const money = (n) => "$" + Number(n).toFixed(2).replace(/\.00$/, "");

// "2026-11-15" + "12:00" -> a readable date in the visitor's own time zone.
function formatWhen(date, time) {
  const [y, m, d] = date.split("-").map(Number);
  const [h, min] = time.split(":").map(Number);
  return new Date(y, m - 1, d, h, min).toLocaleString([], { weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// A message in place of the results (used for errors and the empty state).
function showMessage(className, text) {
  results.replaceChildren(el("p", { className, textContent: text }));
}

// Loading the data ------------------------------------------------------------------------

// Asks the backend for this event and its spots in ONE request, then draws the page.
// The backend returns {event: {...}, listings: [...]} with the spots already sorted closest first.
async function load() {
  if (!eventId) {
    document.getElementById("event-title").textContent = "Pick an event";
    showMessage("muted", "Go back to All events and choose an event to see its parking spots.");
    return;
  }
  try {
    const res = await fetch(`${API}/events/${encodeURIComponent(eventId)}/listings`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Couldn’t load this event (" + res.status + ").");
    render(data.event, data.listings);
  } catch (err) {
    document.getElementById("event-title").textContent = "Something went wrong";
    showMessage("status-error", err.message);
  }
}

// Drawing the page -------------------------------------------------------------------------

// Fills in the heading, then either the empty message or the map and list.
function render(ev, listings) {
  document.title = ev.name + " parking · GameDay Parking";
  document.getElementById("event-title").textContent = ev.name;
  document.getElementById("event-sub").textContent = ev.venue + " · " + formatWhen(ev.date, ev.time);

  // Empty state: no spots listed for this event yet.
  if (!listings.length) {
    showMessage("empty-state", "There are currently no spots available.");
    return;
  }

  const cards = [], pins = [];   // kept so that clicking a pin can highlight its card, and the other way round

  // Marks spot number i as selected in both the map and the list.
  const highlight = (i) => {
    cards.forEach((c, j) => c.classList.toggle("on", i === j));
    pins.forEach((p, j) => p.classList.toggle("on", i === j));
  };

  // ---- The map ----
  // Drawn as an SVG from the latitude/longitude we already have, so it makes no calls to a map service and costs nothing.
  const W = 420, H = 340, cx = W / 2, cy = H / 2;
  // Convert each spot's position to metres east/north of the venue (1 degree of latitude is about 110,540 m).
  const offsets = listings.map((l) => ({
    dx: (l.lng - ev.lng) * Math.cos((ev.lat * Math.PI) / 180) * 111320,
    dy: (ev.lat - l.lat) * 110540,   // minus, because on screen "down" is south
  }));
  // Scale the map so the farthest spot (plus a margin) fits inside it. radius is the map's size in pixels.
  const reach = Math.max(300, ...listings.map((l) => l.dist)) * 1.25;
  const radius = Math.min(cx, cy) - 22;

  const map = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "map", role: "img", "aria-label": "Map of parking spots around " + ev.venue });
  // Two dashed rings with their distances, so the pins have a sense of scale.
  [0.5, 1].forEach((f) => {
    map.append(svg("circle", { class: "map-ring", cx, cy, r: radius * f }));
    map.append(svg("text", { class: "map-label", x: cx, y: cy - radius * f - 4 }, miles(reach * f)));
  });
  // The venue sits in the middle.
  map.append(svg("rect", { class: "map-venue", x: cx - 9, y: cy - 9, width: 18, height: 18 }));
  map.append(svg("text", { class: "map-venue-label", x: cx, y: cy + 24 }, ev.venue));
  // One numbered pin per spot. Pins can be used with the keyboard (Enter or Space) as well as the mouse.
  listings.forEach((l, i) => {
    const pin = svg("g", {
      class: "pin", tabindex: 0, role: "button",
      "aria-label": `Spot ${i + 1}: ${money(l.price)}, ${l.walk} minute walk`,
      transform: `translate(${cx + (offsets[i].dx / reach) * radius},${cy + (offsets[i].dy / reach) * radius})`,
    });
    pin.append(svg("circle", { r: 12 }), svg("text", { y: 4.5 }, String(i + 1)));
    pin.addEventListener("click", () => { highlight(i); cards[i].scrollIntoView({ block: "nearest", behavior: "smooth" }); });
    pin.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pin.dispatchEvent(new Event("click")); } });
    pins.push(pin);
    map.append(pin);
  });

  // ---- The list ----
  // One card per spot: address, price, distance, walking time, hours, flags and security details.
  const list = el("ul", { className: "spot-list" }, listings.map((l, i) => {
    const card = el("li", { className: "spot" },
      el("div", { className: "spot-top" },
        el("strong", {}, el("span", { className: "spot-num", textContent: String(i + 1) }), l.address),
        el("span", { className: "spot-price", textContent: money(l.price) })),
      el("p", { className: "spot-line muted", textContent: `${miles(l.dist)} from the venue · ${l.walk} min walk` }),
      el("p", { className: "spot-line muted", textContent: `Available ${l.start}–${l.end}` }),
      el("div", {},
        l.stacked ? el("span", { className: "flag", textContent: "Stacked parking" }) : "",
        l.overstay > 0 ? el("span", { className: "flag", textContent: money(l.overstay) + " overstay fee / 15 min" }) : ""),
      l.security ? el("p", { className: "spot-line", textContent: "Security: " + l.security }) : "");
    card.addEventListener("click", () => highlight(i));
    cards.push(card);
    return card;
  }));

  results.replaceChildren(
    el("p", { className: "muted", textContent: listings.length + (listings.length === 1 ? " spot" : " spots") + ", closest first" }),
    el("div", { className: "browse-layout" }, map, list));
}

load();
