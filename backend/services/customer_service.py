"""
Customer Service module for retrieving customer data and context.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class Customer:
    first_name: str
    last_name: str
    phone_primary: str


@dataclass
class Equipment:
    equipment_type: str  # 'hvac', 'hot_water_heater', 'furnace'


@dataclass
class CustomerContext:
    customer_name: str
    equipment_type: str
    last_service_date: date | None
    current_date: date
    available_time_windows: list[str]


class CustomerService:
    """Service class for customer data operations"""

    # Hardcoded demo data - simplified for templates
    _customer_data = {
        "+15551234567": {
            "customer_name": "John Smith",
            "equipment_type": "furnace",
            "last_service_date": date(2024, 1, 15),
        },
        "+15559876543": {
            "customer_name": "Sarah Johnson",
            "equipment_type": "hvac",
            "last_service_date": date(2023, 9, 20),
        },
        "+15555551212": {
            "customer_name": "Mike Davis",
            "equipment_type": "hot_water_heater",
            "last_service_date": date(2024, 2, 10),
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

        return {
            "current_date": customer_context.current_date.strftime("%Y-%m-%d"),
            "last_service_date": last_service_date,
            "available_time_windows": ", ".join(
                customer_context.available_time_windows[:5]
            ),  # First 5 slots
            "customer_name": customer_context.customer_name,
            "equipment_type": customer_context.equipment_type,
        }
