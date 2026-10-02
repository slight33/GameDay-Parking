## Team and Project

- Project Name: GameDay Parking.
- Team Name: N/A 
- Team Members:
    - Sean Light, seanlight@lewisu.edu, skilled in backend development, API integration, and working with databases.   

1. The user creates a guest account:
A new user signs up with a name, username, email, phone number, and password. The system hashes the password before storing it and creates the account with guest privileges by default.  Every account starts as a guest and can book listings immediately. If the email or username is already in use, the system rejects the signup and prompts the user to choose a different one.

 2. Guest verifies an address to become a host:
A guest who wants to list a parking spot submits an address and confirms it is accurate. The system validates that the address is a real, geocodable location and, if valid, upgrades the account to host privileges, allowing the user to create listings tied to that address. If the address cannot be geocoded, the system rejects the submission and asks the user to re-enter it.

 3. The user logs in to access their account:
A returning user enters their email and password. The system verifies the credentials against the stored hash and, if valid, grants access to the user's dashboard. If the credentials are invalid, the system displays an error and does not grant access.

 4. The guest browses events and views nearby listings:
A guest selects an event from a list of upcoming events for the supported venues. The system displays available host listings near that venue as both a list and a map, showing each listing's price, distance and walking time to the venue, security details, and whether the spot requires stacked parking. If no listings exist yet for that event, the system displays a message indicating there are currently no spots available.

 5. The host creates a parking listing for an event.
A host selects an event their address is near and fills out a listing form specifying price, the allotted time window, an overstay fee, security details, photos to be shown, and whether the spot involves stacked parking. The system geocodes the host's address to place a pin on the map and calculates walking distance to the venue. Once submitted, the listing becomes visible to guests browsing that event.

 6. The guest views a listing's neighborhood safety score and photos before booking.
Before committing to a listing, a guest can view a neighborhood safety score and any photos the host has provided for the parking spot. This gives out of town guests unfamiliar with the area added confidence for the spot's location before they pay. 

 7. Guest books and pays for a parking spot.
A guest selects a listing, confirms a time window, and enters license plate information, then pays through Stripe (test mode) at the time of booking. On a successful charge, the system marks the spot as reserved for that time window so it cannot be double booked. If the payment fails, the booking is not created and the listing remains available to other guests.

 8. The system exchanges confirmation details after a booking is completed.
Once a booking is confirmed, the system automatically shares the guest's contact info, license plate number, and confirmed time window with the host, and shares the host's contact info, a receipt, and a summary of the parking spot details with the guest. This removes the need for either party to manually request information before the guest arrives.

 9. The host views their dashboard of listings and bookings.
A logged in host sees a dashboard listing the spots they've created, along with any confirmed bookings against each one, including the guest's contact info and license plate for upcoming reservations. If a host has no active listings, the dashboard displays a prompt to create one.

 10. The guest views their dashboard of bookings.
A logged in guest sees a dashboard of their upcoming and past bookings, each showing the host's contact info, spot details, and receipt. If a guest has no bookings, the dashboard displays a prompt to browse upcoming events.
