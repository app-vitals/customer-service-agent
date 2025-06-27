"""
Customer Service module for retrieving customer data and context.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any


@dataclass
class Customer:
    first_name: str
    last_name: str
    phone_primary: str


@dataclass
class CallHistory:
    call_direction: str  # 'inbound', 'outbound'
    call_outcome: str  # 'scheduled', 'voicemail', 'no_answer', 'completed'
    created_at: datetime
    notes: str


@dataclass
class Equipment:
    equipment_type: str  # 'hvac', 'hot_water_heater', 'furnace'


def _days_ago(days: int) -> datetime:
    """Helper to create datetime relative to today"""
    return datetime.now() - timedelta(days=days)


def _date_days_ago(days: int) -> date:
    """Helper to create date relative to today"""
    return date.today() - timedelta(days=days)


@dataclass
class CustomerContext:
    customer_name: str
    equipment_type: str
    last_service_date: date | None
    current_date: date
    available_time_windows: list[str]
    call_history: list[CallHistory]


class CustomerService:
    """Service class for customer data operations"""

    # Hardcoded demo data - simplified for templates
    _customer_data = {
        "+15551234567": {
            "customer_name": "John Smith",
            "equipment_type": "furnace",
            "last_service_date": _date_days_ago(365),  # 1 year ago
            "call_history": [
                CallHistory(
                    call_direction="outbound",
                    call_outcome="voicemail",
                    created_at=_days_ago(3),
                    notes="annual maintenance scheduling",
                )
            ],
        },
        "+15559876543": {
            "customer_name": "Sarah Johnson",
            "equipment_type": "hvac",
            "last_service_date": _date_days_ago(280),  # ~9 months ago
            "call_history": [],
        },
        "+15555551212": {
            "customer_name": "Mike Davis",
            "equipment_type": "hot_water_heater",
            "last_service_date": _date_days_ago(135),  # ~4.5 months ago
            "call_history": [
                CallHistory(
                    call_direction="outbound",
                    call_outcome="voicemail",
                    created_at=_days_ago(1),
                    notes="water heater service reminder",
                )
            ],
        },
    }

    # Standard available time windows for scheduling
    _available_time_windows = [
        "Monday 9:00 AM - 12:00 PM",
        "Monday 1:00 PM - 5:00 PM",
        "Tuesday 9:00 AM - 12:00 PM",
        "Tuesday 1:00 PM - 5:00 PM",
        "Wednesday 9:00 AM - 12:00 PM",
        "Wednesday 1:00 PM - 5:00 PM",
        "Thursday 9:00 AM - 12:00 PM",
        "Thursday 1:00 PM - 5:00 PM",
        "Friday 9:00 AM - 12:00 PM",
        "Friday 1:00 PM - 5:00 PM",
    ]

    @classmethod
    def find_by_phone_number(cls, phone_number: str) -> CustomerContext:
        """
        Find customer by phone number and return complete context for template rendering.
        For demo purposes, always returns the same customer data.

        Args:
            phone_number: Customer phone number (ignored for demo)

        Returns:
            CustomerContext with demo customer data
        """
        # Fallback to John Smith data for demo
        demo_data = cls._customer_data.get(
            phone_number, cls._customer_data["+15551234567"]
        )

        return CustomerContext(
            customer_name=demo_data["customer_name"],
            equipment_type=demo_data["equipment_type"],
            last_service_date=demo_data["last_service_date"],
            current_date=date.today(),
            available_time_windows=cls._available_time_windows,
            call_history=demo_data["call_history"],
        )

    @classmethod
    def get_template_context(cls, phone_number: str) -> dict[str, Any]:
        """
        Get template context dictionary for Jinja2 rendering.
        For demo purposes, always returns the same customer data.

        Args:
            phone_number: Customer phone number (ignored for demo)

        Returns:
            Dictionary with all template variables
        """
        customer_context = cls.find_by_phone_number(phone_number)
        last_service_date = (
            customer_context.last_service_date.strftime("%Y-%m-%d")
            if customer_context.last_service_date
            else "No previous service"
        )

        # Format call history for template
        if not customer_context.call_history:
            call_history_text = "No recent calls"
        else:
            history_items = []
            current_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            for call in customer_context.call_history:
                days_ago = (
                    current_date
                    - call.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
                ).days
                day_text = "yesterday" if days_ago == 1 else f"{days_ago} days ago"
                history_items.append(
                    f"We called {day_text} and left a {call.call_outcome} about {call.notes}"
                )
            call_history_text = "; ".join(history_items)

        return {
            "current_date": customer_context.current_date.strftime("%Y-%m-%d"),
            "last_service_date": last_service_date,
            "available_time_windows": ", ".join(
                customer_context.available_time_windows[:5]
            ),  # First 5 slots
            "customer_name": customer_context.customer_name,
            "equipment_type": customer_context.equipment_type,
            "call_history": call_history_text,
        }
