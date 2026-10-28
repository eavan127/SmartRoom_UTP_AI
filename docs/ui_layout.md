# SmartRoom UTP kiosk: interface and navigation design

Prototype: [prototype/index.html](../prototype/index.html), one HTML file you open in a browser.
Target device: landscape touch kiosk beside the locker, 1280 × 800.

## 1. Visual style (taken from the IRC website, ulibrary.utp.edu.my)

| Token | Hex | Where IRC uses it | Where the kiosk uses it |
|---|---|---|---|
| Navy | `#324773` | "IRC" logo, menu button | Brand mark, titles, current step, Collect tile |
| Deep navy | `#061E2F` | Footer | Hero banner gradient, locker body |
| Gold | `#C48D0C` | Logo accent, ChatBot tab | Top bar underline, simulation banner, step number |
| Sage green | `#749082` | "About Us" pill buttons | Primary buttons, success, Verified chips |
| Cream | `#EBE3C7` | Section panels | Card header strips |
| Light grey | `#F3F3F3` | Page background | Page background |
| Red | `#A8322D` | (not used by IRC) | Denied only |

Font: IRC uses Museo Sans with Segoe UI as fallback. The kiosk uses Segoe UI. Buttons are rounded pills like IRC's.

## 2. Fixed screen grid (same on every screen)

```
+--------------------------------------------------------------------------+
| TOP BAR  [IRC | SmartRoom UTP]               [time/date] [Home] [Staff]  |  top
+--------------------------------------------------------------------------+
| MODE STRIP  gold = student (prototype), navy = staff mode                 |
| STEP TRACKER   1 Choose booking > 2 Face scan > 3 Collect/Return > 4 Done |
+-----------------------------------------------+--------------------------+
| MAIN TASK (left, 2/3)                         | INFO PANEL (right, 1/3)  |
|  title + one-line instruction                 |  Your booking: room,     |
|  the one thing to do on this screen           |  slot, locker, members   |
|  (list / camera / result)                     |  with status chips       |
|                                               |  Tips / Help             |
+-----------------------------------------------+--------------------------+
| ACTION BAR  [< Back / Cancel]      hint text      [Primary action >]      |  bottom
+--------------------------------------------------------------------------+
```

Rules:
- **Back / Cancel is always bottom-left. The main action is always bottom-right** (green). Users never have to search for the next button.
- **Home and Staff are always top-right and never move.** Home is greyed out on the home screen, not hidden.
- In staff mode the Staff button turns gold and reads **Exit staff**, and the strip under the top bar turns navy, so it is always clear which mode you are in. Exit staff goes back to the student screen it came from, such as a denied verification, or to Home.
- Every row (top bar, step tracker, content, action bar) shares one 1280 px column with 32 px side padding, so all left and right edges line up on any screen width.
- The left side shows what to do now. The right side shows the booking status.
- One main task per screen. Large touch targets (at least 48 px high).
- Colour carries meaning: green = verified/approved, red = denied, gold = information.

## 3. Screens and navigation

```
Home --Collect--> Select booking --Select--> Face scan --all verified--> Approved (locker open) --> Done --> Home
  |                                              |
  |                                              +--3 failed scans--> Denied --Try again--> Face scan
  |                                                                     +--Call staff--> Staff (PIN) --Override--> Approved
  +--Return--> Select card out --> Face scan --> Locker open (put card in) --> Thank you --> Home
Staff (top-right, any screen): Override | Card log | Settings
```

| # | Screen | Left (main) | Right (panel) | Bottom-left | Bottom-right |
|---|---|---|---|---|---|
| 01 | Home | Welcome banner, two big tiles: **Collect** (left, navy), **Return** (right, green outline), How it works | – | – | – |
| 02 | Choose booking | Search box, today's bookings as cards with status badge and **Select** on each card's right | What happens next, Need help | Back | – |
| 03–05 | Face scan | Status message, camera with face oval, **Scan face** under the camera | Booking, 4 members with Waiting/Verified, progress "2 of 4", attempts left | Cancel | – (moves on by itself when all are verified) |
| 06 | Approved | Locker drawing (door open), "Locker 01 is open", what to take | Booking, all verified | – | I have taken the card |
| 07 | Done | Return-by time, room / slot / verification time | – | – | Finish |
| 08 | Denied | Locker closed, who was not verified, **Try again** (left) and **Call staff** (right) | Booking status | Start over | – |
| 09–11 | Staff | PIN, then tabs: Override, Card log, Settings | Privacy note | Back / Home | – |
| 12–14 | Return | Same screens with the return wording | Same | Same | Card returned, door closed |
