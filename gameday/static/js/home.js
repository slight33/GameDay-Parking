// Number of empty placeholder cards shown while the events load from the backend.
const CARD_COUNT = 6;
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const container = document.getElementById("events");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");

// The sections shown on the home page, in order. The key matches each event's category from the backend.
// Events with any other category go in the last section.
const SECTIONS = [
  { key: "nfl", title: "NFL games" },
  { key: "concert", title: "Concerts" },
  { key: "other", title: "More events" },
];

let allEvents = [];   // every upcoming event from the backend, kept so the page can be redrawn without a new request

let query = "";       // what's typed in the search box
let loaded = false;   // true once the events have arrived, so typing early doesn't hide the placeholders

// Filter as the user types. Pressing Enter or the Search button does the same thing.
searchInput.addEventListener("input", () => {
  query = searchInput.value;
  if (loaded) render();
});
searchForm.addEventListener("submit", (event) => {
  event.preventDefault(); // stops the page from reloading
  query = searchInput.value;
  if (loaded) render();
});

// True if every word typed appears in the event's name or venue, in any order.
// So "bills dolphins" finds "Buffalo Bills vs. Miami Dolphins".
function matches(ev, words) {
  const text = `${ev.name} ${ev.venue}`.toLowerCase();
  return words.every((w) => text.includes(w));
}

// Turns "2026-11-15" and "12:00" into something readable, in the visitor's own time zone.
function formatWhen(date, time) {
  const [y, m, d] = date.split("-").map(Number);
  const [h, min] = time.split(":").map(Number);
  return new Date(y, m - 1, d, h, min).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// A short message shown in place of the events (used for "no events" and error messages).
function gridNote(text) {
  const p = document.createElement("p");
  p.className = "grid-note";
  p.textContent = text;
  return p;
}

// Empty placeholder cards shown while the events load.
function renderEmptyCards(count) {
  const grid = document.createElement("div");
  grid.className = "card-grid";
  for (let i = 0; i < count; i++) {
    const card = document.createElement("div");
    card.className = "card";
    grid.append(card);
  }
  container.replaceChildren(grid);
}

// Builds one clickable card. It links to the browse page with the event's id in the URL
// (browse.html?event=...) so that page knows which event's parking spots to show.
// textContent is used (not innerHTML) so text from the database can never run as code.
function eventCard(ev) {
  const card = document.createElement("a");
  card.className = "card event-card";
  card.href = `/static/browse.html?event=${encodeURIComponent(ev.id)}`;

  const name = document.createElement("h3");
  name.textContent = ev.name;
  const venue = document.createElement("p");
  venue.textContent = ev.venue;
  const when = document.createElement("p");
  when.className = "event-when";
  when.textContent = formatWhen(ev.date, ev.time);
  const spots = document.createElement("p");
  spots.className = "event-spots";
  spots.textContent = ev.spots === 0 ? "No spots yet" : ev.spots + (ev.spots === 1 ? " spot" : " spots");

  card.append(name, venue, when, spots);
  return card;
}

// Draws the page from allEvents: filter, then sort, then group into sections, then draw.
// The search and sort steps will plug in here, so everything redraws through this one function.
function render() {
  // Filter step: keep events that match the search.
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const list = allEvents.filter((ev) => matches(ev, words));   // already sorted by date and time by the backend

  container.replaceChildren();
  if (!list.length) {
    container.append(gridNote(words.length
      ? `No events match "${query.trim()}". Try a team, artist, or stadium.`
      : "No upcoming events right now."));
    return;
  }


  const keys = SECTIONS.map((s) => s.key);
  for (const section of SECTIONS) {
    // An event goes in its category's section, or in the last one if its category isn't listed.
    const events = list.filter((ev) => (keys.includes(ev.category) ? ev.category : "other") === section.key);
    if (!events.length) continue;   // skip empty sections

    const heading = document.createElement("h2");
    heading.className = "section-title";
    heading.textContent = section.title;
    const grid = document.createElement("div");
    grid.className = "card-grid";
    events.forEach((ev) => grid.append(eventCard(ev)));
    container.append(heading, grid);
  }
}

// Asks the backend for the upcoming events, keeps them, and draws them. One request, no polling.
// Past events are also hidden here using the visitor's local date.
async function loadEvents() {
  renderEmptyCards(CARD_COUNT);   // placeholders while we wait
  try {
    const res = await fetch(`${API}/events`);
    if (!res.ok) throw new Error("Server returned " + res.status);
    const now = new Date();
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    allEvents = (await res.json()).filter((ev) => ev.date >= today);
    loaded = true;
    render();
  } catch (err) {
    console.error(err);
    container.replaceChildren(gridNote("Couldn’t load events. Try again in a moment."));
  }
}
loadEvents();
const TOKEN_KEY = "gdp-token";

// If a token is saved, ask the backend who it belongs to and show their username.
async function showUser() {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return; // not logged in, so keep the Log in / Sign up buttons

  try {
    const res = await fetch(`${API}/me`, { headers: { Authorization: "Bearer " + token } });
    if (!res.ok) {
      localStorage.removeItem(TOKEN_KEY); // expired or invalid token
      return;
    }
    const user = await res.json();
    const actions = document.getElementById("account-actions");
actions.innerHTML =
  '<span class="user-name"></span>' +
  (user.role === "guest"
    ? '<a class="btn btn-accent" href="/host_upgrade">Become a host</a>'
    : '<a class="btn btn-ghost" href="/my_listings">My listings</a>' +
      '<a class="btn btn-accent" href="/create_listing">Create listing</a>') +
  // >>> DASHBOARD (new): "Dashboard" opens the page with upcoming and past bookings, host details and receipts.
  '<a class="btn btn-ghost" href="/dashboard">Dashboard</a>' +
  // <<< END DASHBOARD
  // "My bookings" opens the page where a guest can see their bookings and cancel one.
  '<a class="btn btn-ghost" href="/my_bookings">My bookings</a>' +
  '<button type="button" class="btn btn-ghost" id="logout-button">Log out</button>';
actions.querySelector(".user-name").textContent = user.username;
document.getElementById("logout-button").addEventListener("click", logout);
  } catch (err) {
    console.error(err);
  }
}
// Delete the saved token and reload the home page, which brings back the Log in / Sign up buttons.
function logout() {
  localStorage.removeItem(TOKEN_KEY);
  window.location.href = "/";
}
showUser();