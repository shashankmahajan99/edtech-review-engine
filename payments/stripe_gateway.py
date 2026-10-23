"""
Stripe Payment Gateway Integration.
Generates hosted Checkout Sessions for Paid Pilots ($150) and Monthly Retainers ($1,500–$3,500/mo).
"""

import os
from typing import Dict, Any, Optional

try:
    import stripe
except ImportError:
    stripe = None

PACKAGES = {
    "paid_pilot": {
        "name": "Desk Paid Pilot (5 Urgent Essay Reviews)",
        "amount_usd": 15000, # $150.00
        "mode": "payment",
        "description": "5 full essay reviews within 6h. 100% credited toward your first month's retainer upon signing."
    },
    "starter": {
        "name": "Desk Starter Retainer (50 Reviews / mo)",
        "amount_usd": 150000, # $1,500.00
        "mode": "subscription",
        "description": "Up to 50 standard reviews per month for solo admissions consultants ($30/review)."
    },
    "pro": {
        "name": "Desk Pro Retainer (100 Reviews / mo)",
        "amount_usd": 250000, # $2,500.00
        "mode": "subscription",
        "description": "Up to 100 reviews per month with priority 6h SLA and dedicated WhatsApp desk ($25/review)."
    },
    "enterprise": {
        "name": "Desk Enterprise Retainer (150 Reviews / mo)",
        "amount_usd": 350000, # $3,500.00
        "mode": "subscription",
        "description": "Up to 150 reviews per month with multi-seat role access and custom rubric calibration."
    }
}


class StripeGateway:
    def __init__(self):
        self.api_key = os.environ.get("STRIPE_SECRET_KEY")
        if self.api_key and stripe:
            stripe.api_key = self.api_key

    def create_checkout_session(
        self,
        package_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        pkg = PACKAGES.get(package_id, PACKAGES["pro"])

        # If live Stripe API key is available
        if self.api_key and stripe:
            try:
                line_item = {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": pkg["name"],
                            "description": pkg["description"],
                        },
                        "unit_amount": pkg["amount_usd"],
                    },
                    "quantity": 1,
                }
                if pkg["mode"] == "subscription":
                    line_item["price_data"]["recurring"] = {"interval": "month"}

                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[line_item],
                    mode=pkg["mode"],
                    customer_email=customer_email,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                return {"url": session.url, "session_id": session.id, "mode": "live"}
            except Exception as e:
                print(f"[!] Stripe API error: {e}. Falling back to simulation.")

        # Staging / Demo Checkout URL
        simulated_url = f"{success_url}?session_id=sim_{package_id}_{int(os.getpid())}&package={package_id}"
        return {
            "url": simulated_url,
            "session_id": f"sim_{package_id}",
            "mode": "simulation",
            "package_name": pkg["name"],
            "amount_usd": pkg["amount_usd"] / 100
        }


if __name__ == "__main__":
    gw = StripeGateway()
    session = gw.create_checkout_session(
        "pro",
        "counselor@firm.com",
        "https://apexreview.co/success",
        "https://apexreview.co/cancel"
    )
    print("[*] Generated Checkout Session:", session)
