# 📱 Push Notification Rules for Locker App

This document details all types of push notifications for **Buyers** and **Stores**, including the trigger conditions, timing, title, and message contents.

---

## 🧍‍♂️ Buyer

| # | Condition | Timing | Title | Message |
|---|------------|---------|--------|----------|
| 1 | When the combo pickup deadline has passed and the buyer has not picked it up | Immediately after the pickup period expires | Combo Pickup Deadline Passed | Locker... Item No.●●● (XXX) pickup period has expired. The locker is locked and cannot be opened. |
| 2 | When the combo's expiration date has passed | Immediately after expiration | Combo Expired | Item No.●●● (XXX) has expired. Please do not consume and dispose of it safely. |
| 3 | When a favorite store publishes a new Combo | Immediately after the store publishes | New Combo from Your Favorite Store! | Your favorite store [Store Name] has released a new Combo. Check it out on the app! |
| 4 | When the Combo pickup deadline is approaching | 5 minutes before the pickup deadline | 5 Minutes Left to Pick Up | Only 5 minutes left to pick up item No.●●● (XXX). Please come to the locker soon. |
| 5 | When the buyer cancels an order (refund notification) | Immediately after cancellation | Order Canceled | Order No.●●● (XXX) has been canceled. A 70% refund is being processed. |

---

## 🏪 Store

| # | Condition | Timing | Title | Message |
|---|------------|---------|--------|----------|
| 1 | When a buyer completes a Combo reservation | Immediately after reservation confirmation | Combo Reserved | Item No.●●● (XXX) has been reserved. Please wait until pickup is completed. |
| 2 | When a buyer cancels a reservation | Immediately after cancellation | Combo Reservation Canceled | Item No.●●● (XXX) has been canceled. |
| 3 | When a buyer successfully picks up a Combo | Immediately after pickup confirmation | Combo Pickup Completed | Buyer has successfully picked up item No.●●● (XXX). Thank you for using the locker. |
| 4 | When the sales period ends and the Combo is not reserved | Immediately after the sales period ends | Combo Not Reserved | Item No.●●● (XXX) sales period has ended without any reservations. |
| 5 | When a buyer posts a Combo review | Immediately after review submission | New Review Received | A new review has been posted for item No.●●● (XXX): “Review content～～～” |
| 6 | When the deadline for placing a Combo into the locker is approaching | 5 minutes before the deadline | 5 Minutes Left to Place Combo in Locker | Locker [Locker Name], Compartment ● — Only 5 minutes left to place the Combo. |

---

📘 *This document is compiled from the original push notification configuration sheet (Locker App).*

