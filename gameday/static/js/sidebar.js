// Adds the same sidebar to every page that loads this file. Its links change with who's logged in.
// Everything is wrapped in a function so names like API don't clash with the page's own script.
(function () {
  const API = ["localhost", "127.0.0.1"].includes(location.hostname)
    ? ""
    : "https://gameday-parking.onrender.com";
  const TOKEN_KEY = "gdp-token";

  // Makes one sidebar link, and marks it if it's the page you're on.
  function link(href, text) {
    const a = document.createElement("a");
    a.className = "sidebar-link";
    a.href = href;
    a.textContent = text;
    if (location.pathname === href) a.setAttribute("aria-current", "page");
    return a;
  }

  // Returns the logged-in user, or null if nobody is logged in or the token has expired.
  async function getUser() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;
    try {
      const res = await fetch(`${API}/me`, { headers: { Authorization: "Bearer " + token } });
      return res.ok ? await res.json() : null;
    } catch {
      return null;
    }
  }

  const nav = document.createElement("nav");
  nav.className = "sidebar";
  nav.id = "sidebar";
  nav.setAttribute("aria-label", "Main");

  const brand = document.createElement("a");
  brand.className = "sidebar-brand";
  brand.href = "/";
  brand.textContent = "GameDay Parking";
  nav.append(brand, link("/", "Events"));

  // The dark layer behind the sidebar on phones. Tapping it closes the sidebar.
  const backdrop = document.createElement("div");
  backdrop.className = "sidebar-backdrop";

  // The Menu button, only visible on narrow screens.
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "sidebar-toggle";
  toggle.textContent = "Menu";
  toggle.setAttribute("aria-controls", "sidebar");
  toggle.setAttribute("aria-expanded", "false");

  function setOpen(open) {
    nav.classList.toggle("open", open);
    backdrop.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }
  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("open")));
  backdrop.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });

  // Add everything to the page. The Menu button goes at the start of the page's header.
  document.body.classList.add("has-sidebar");
  document.body.prepend(nav, backdrop);
  const header = document.querySelector("header");
  const headerInner = header && header.querySelector(".header-inner");
  (headerInner || header || document.body).prepend(toggle);

  // Once we know who's logged in, add the links for them.
  getUser().then((user) => {
    if (!user) {
      nav.append(link("/login", "Log in"), link("/register", "Sign up"));
      return;
    }

    const who = document.createElement("p");
    who.className = "sidebar-user";
    who.textContent = `Signed in as ${user.username}` + (user.role === "host" ? " (host)" : "");
    brand.after(who);

    nav.append(link("/my_bookings", "My bookings"), link("/dashboard", "Dashboard"));
    if (user.role === "host") {
      nav.append(link("/my_listings", "My listings"), link("/create_listing", "Create listing"));
    } else {
      nav.append(link("/host_upgrade", "Become a host"));
    }

    const spacer = document.createElement("div");
    spacer.className = "sidebar-spacer";
    const logout = document.createElement("button");
    logout.type = "button";
    logout.className = "sidebar-link";
    logout.textContent = "Log out";
    logout.addEventListener("click", () => {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = "/";
    });
    nav.append(spacer, logout);
  });
})();