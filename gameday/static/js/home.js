// Number of empty placeholder cards shown while the events load from the backend.
const CARD_COUNT = 6;
const API = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? ""
  : "https://gameday-parking.onrender.com";
const grid = document.getElementById("event-grid");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");


function renderEmptyCards(count) {
  for (let i = 0; i < count; i++) {
    const card = document.createElement("div");
    card.className = "card";
    grid.append(card);
  }
}

searchForm.addEventListener("submit", (event) => {
  event.preventDefault(); // stops the page from reloading
  console.log("Search:", searchInput.value.trim()); // TODO: search events once the backend has them
});

// Turns "2026-11-15" and "12:00" into something readable, in the visitor's own time zone.
function formatWhen(date, time) {
  const [y, m, d] = date.split("-").map(Number);
  const [h, min] = time.split(":").map(Number);
  return new Date(y, m - 1, d, h, min).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// Draws one clickable card per event. Each card links to the browse page and puts the event's id in the URL
// (browse.html?event=v2) so that page knows which event's parking spots to show.
// textContent is used (not innerHTML) so text from the database can never run as code.
function renderEvents(events) {
  grid.replaceChildren();
  if (!events.length) {
    grid.append(gridNote("No upcoming events right now."));
    return;
  }
  events.forEach((ev) => {
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
    grid.append(card);
  });
}

// A short message that fills the whole card grid (used for "no events" and error messages).
function gridNote(text) {
  const p = document.createElement("p");
  p.className = "grid-note";
  p.textContent = text;
  return p;
}

// Asks the backend for the upcoming events and draws them. One request, no polling.
// Past events are also hidden here using the visitor's local date.
async function loadEvents() {
  renderEmptyCards(CARD_COUNT);   // placeholders while we wait
  try {
    const res = await fetch(`${API}/events`);
    if (!res.ok) throw new Error("Server returned " + res.status);
    const now = new Date();
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    renderEvents((await res.json()).filter((ev) => ev.date >= today));
  } catch (err) {
    console.error(err);
    grid.replaceChildren(gridNote("Couldn’t load events. Try again in a moment."));
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
  (user.role === "guest" ? '<a class="btn btn-accent" href="/host_upgrade">Become a host</a>' : '') +
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