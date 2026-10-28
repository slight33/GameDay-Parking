// Number of empty event cards to show until events come from the backend.
const CARD_COUNT = 6;

const grid = document.getElementById("event-grid");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const res = await fetch(`${API}/me`, { headers: { Authorization: "Bearer " + token } });

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

renderEmptyCards(CARD_COUNT);
const TOKEN_KEY = "gdp-token";

// If a token is saved, ask the backend who it belongs to and show their username.
async function showUser() {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return; // not logged in, so keep the Log in / Sign up buttons

  try {
    const res = await fetch("/me", { headers: { Authorization: "Bearer " + token } });
    if (!res.ok) {
      localStorage.removeItem(TOKEN_KEY); // expired or invalid token
      return;
    }
    const user = await res.json();
    const actions = document.getElementById("account-actions");
    actions.innerHTML =
  '<span class="user-name"></span>' +
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