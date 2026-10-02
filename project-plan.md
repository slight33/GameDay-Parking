# Project Plan

## 1. Title and Tagline - What is the project called, and what's it about?

The title of this project is *GameDay Parking - Peer to Peer Parking*

## 2. Problem - What problem are we solving?

Parking availability is one of the biggest challenges that large events face.
Thousands of fans circle event venues looking for a spot, often paying inflated
prices to informal lots. Meanwhile, homeowners near the venue who
want to rent out their driveway currently have to stand outside with a sign and
flag down passing cars, accepting cash from strangers with no record of who is
coming, when, or for how long.
 
GameDay Parking is a web application that connects homeowners near an event with
fans who need a reliable, pre-arranged parking spot. It formalizes a transaction
that already happens informally: payment is made at booking instead of in cash,
and both sides receive the information they need to feel secure. It removes the
guesswork and awkwardness for both hosts and guests, and lets fans (especially
out of town fans) focus on the event instead of worrying about where to park.

## 3. Users - Who is this for?

There are 2 types of users for this project:

  Hosts: Homeowenrs near a stadium or event venue who want to rent out their driveway or parking spot for a time period for some extra money.  

  Guests: The fans that are attending an event and want a pre-arranged and verified parking spot near the stadium.  This includes users who are coming from out of state and are unfamiliar with the area.

## 4. Team members - Who is working on this and how are they qualified?

The following people are working on this project:

- Sean Light: Back-end and database developer. Sean has an assoiciates degree in software development and certifications in python and C++. He has built backend projects utilizing api's and databases in course work and personal projects.

- Partner 2: Front-end and integrations developer.     

## 5. Features - What does the MVP need?

- Account signup and login, where each account can act as a host, guest, or both.
- Event page displaying a list of upcoming events for a small number of venues. (want to focus on stadiums that are in residential neighborhoods first)
- Host listing form: address, price, allotted time, overstay fee, security details, and whether the space requires stacked parking
- Guest browsing: listings for a selected event, shown as a list along with a simple map with the distance and walking time from each listing to the event
- Booking and payment: The guest books a spot and pays at booking using Stripe (test mode) instead of cash.
- Confirmation exchange: Once booked, the host receives the guests contact information, license plate number, and confirmed time window.  The guest recieves the host's contact information, a receipt, and a summary of the parking spot details.
- Simple host and guest dashboard showing their listings and bookings
- Neighborhood safety score and photos of parking spot.


Explicitly excluded from MVP:
- Real host payouts via stripe.
- Complete ticketmaster discovery api integration.
- Native mobile app.
- Internal communication between the host and guest.

## 6. Data - What are we storing?

Data is stored in a PostgreSQL database.
- Users: Name, username, email, phone number, and a hashed password
- Events: Name, venue, address, and date and time
- Listings: host, address, coordinates, price, allotted time window, overstay fee, security details, stacked parking flag, and the event it is attached to.
- Bookings: listing, guest, license plate number, time window, and if its booked.
- Payments: Stripe payment reference, amount, status, and linked to booking.

Authentication will be limited to email and password login with role-based access.  Card numbers are not stored by the application as stripe handles that.

## 7. Tech - What stack are we using?

- Frond end: React with HTML, CSS, and Javascript for a responive interface.
- Back-end: Python 3.12 with FastAPI for the authentication, listing and booking logic, and routing between the database and API's.
- Database: PostgreSQL
- Git: version control
- Payment: Stripe in test mode for payment at booking.
- Maps: Leaflet for a free map service, opencage geocoding for pins on map, and OpenRouteService for walking distance.
- Testing: pytest for unit and integration tests, including a concurrency test to ensure double-bookings are prevented. Stripe tests for payment and to confirm the bookings and charges are accurate.

## 8. Related work - Who has done similar work before?

Several existing products handle parking reservations or peer-to-peer rentals.

- SpotHero:  lets drivers reserve and pay for parking in garages and lots ahead of time, including for events. It shows that drivers value a guaranteed, pre-paid spot, but it is built around commercial lots rather than individual homeowners.
- ParkWhiz: offers a similar reservation model for event and daily parking. It confirms the demand for event-specific parking, while the supply side is still mostly commercial.
- DIBS Parking: lets homeowners and lot owners list driveways and private lots near stadiums and arenas. It is the closest existing product to this project and would essientally be a direct competitor. Listings show price and walking time, hosts see who is coming and their license plate before arrival, and hosts are paid out through Stripe. DIBS shows that peer-to-peer event parking is viable.

GameDay Parking follows the same core model as DIBS: homeowners list their driveways, and guests reserve and pay in advance. Rather than compete with these platforms feature for feature, this project focuses on a narrower slice of the problem. It would launch around specific venues, where the goal is to build enough listings per event that guests have a real choice, and then expands to more locations. DIPS on the other hand offers parking for basically every game and event, however becouse of this most of the events only offer 2 or 3 spots per event if any at all.




## 9. Monetize - How will this make money?

The platform would charge a service fee on each booking, taken as a percentage of the parking price from the guest, the host, or both. Because the transaction already happens informally, it only needs to offer a safer and more convenient way to complete it. A possible later addition is partnering with venues or event promoters to feature the service on event pages. The MVP does not collect fees or pay out hosts.

## 10. UI/UX - How should this look and feel?

- Event page showing upcoming events, leading to the listings near each event
- Listing view with a map alongside a list, showing price, distance and walking time to the venue, security details, and whether the spot is stacked parking
- Host listing form: a short, guided form for the address, price, time window, overstay fee, and security details
- Guest checkout: a clear booking summary followed by Stripe payment, ending in a confirmation screen
- Confirmation and dashboard views that show the exchanged information (host and guest contact details, license plate, time window, receipt, and spot details) so both sides feel secure before arriving


## 11. Deployment - Where and how will this ship?

- Front end: React hosted on vercel or netlify
- Back end: FastAPI hosted on render or railway along with a managed PostgreSQL database.
- Stripe in test mode with a webhook pointing at the back end.
- env: variables for the db, stripe keys, api and keys.

