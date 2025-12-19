from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    CanteenItem, InventoryStock, InventoryTransaction, School
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError
)

class InventoryService:
    """
    Handles business logic for managing all non-library inventory items, 
    stock levels, and consumption transactions.
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @classmethod
    @transaction.atomic
    def register_canteen_item(
        cls, 
        school_id: int, 
        name: str, 
        unit_price: float, 
        initial_stock: int, 
        is_available: bool = True
    ) -> CanteenItem:
        """
        Registers a new canteen item and initializes its stock.
        """
        school = cls._validate_school_context(school_id)

        # 1. Validation: Price and Stock
        if unit_price <= 0 or initial_stock < 0:
            raise ValidationError("Unit price must be positive and initial stock cannot be negative.")

        # 2. Business Rule: Unique Item Name Check (per school)
        if CanteenItem.objects.filter(school=school, name__iexact=name).exists():
            raise BusinessRuleViolation(f"Canteen item with name '{name}' already exists.")

        # 3. Execution (Creation)
        canteen_item = CanteenItem.objects.create(
            school=school,
            name=name,
            unit_price=unit_price,
            current_stock=initial_stock,
            is_available=is_available
        )

        return canteen_item

    # --- STOCK ADJUSTMENT AND CONSUMPTION ---

    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls, 
        item_id: int, 
        quantity: int, 
        transaction_type: str,
        reason: str,
        related_user=None,
    ) -> InventoryTransaction:
        """
        Generic function to add or remove stock, creating an auditable transaction record.
        This enforces the Inventory Stock Constraint upon removal.
        """
        item = get_object_or_404(CanteenItem, pk=item_id)
        
        # 1. Validation: Quantity and Transaction Type
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
            
        valid_types = dict(InventoryTransaction.TRANSACTION_CHOICES).keys()
        if transaction_type not in valid_types:
             raise ValidationError(f"Invalid transaction type. Must be one of {', '.join(valid_types)}")

        # 2. Business Rule: Inventory Stock Constraint (for removal/consumption)
        if transaction_type == InventoryTransaction.TRANSACTION_TYPE_REMOVAL:
            if item.current_stock < quantity:
                raise BusinessRuleViolation(
                    f"Inventory Stock Constraint Violated: Only {item.current_stock} of '{item.name}' available, cannot remove {quantity}."
                )

        # 3. Execution (Stock Update)
        if transaction_type == InventoryTransaction.TRANSACTION_TYPE_ADDITION:
            item.current_stock += quantity
            new_balance = item.current_stock
        else: # REMOVAL (Consumption, wastage, sale)
            item.current_stock -= quantity
            new_balance = item.current_stock

        item.save(update_fields=['current_stock'])

        # 4. Create Auditable Transaction Record
        transaction_record = InventoryTransaction.objects.create(
            school=item.school,
            item=item,
            transaction_type=transaction_type,
            quantity=quantity,
            reason=reason,
            user=related_user,
            stock_after=new_balance
        )
        
        return transaction_record

    @classmethod
    @transaction.atomic
    def process_canteen_sale(cls, item_id: int, quantity: int, student_id: int, user_context=None) -> InventoryTransaction:
        """
        Handles a specific type of removal: a sale linked to a student purchase.
        This would typically be called by the FinanceService after a successful wallet debit.
        """
        item = get_object_or_404(CanteenItem, pk=item_id)
        
        # 1. Validation: Stock Constraint
        if item.current_stock < quantity:
            raise BusinessRuleViolation(
                f"Cannot process sale: Only {item.current_stock} available, requested {quantity}."
            )

        # 2. Side Effect: Call Finance Service to handle wallet debit
        # NOTE: This enforces the constraint that money must be handled FIRST.
        # total_cost = item.unit_price * quantity
        # from .finance_service import FinanceService
        # try:
        #     FinanceService.process_canteen_purchase(student_id, total_cost, item_id)
        # except BusinessRuleViolation as e:
        #     raise e # Re-raise if fund check failed in finance service

        # 3. Execution (Stock Removal)
        return cls.adjust_stock(
            item_id=item_id,
            quantity=quantity,
            transaction_type=InventoryTransaction.TRANSACTION_TYPE_REMOVAL,
            reason=f"Sale to Student ID {student_id}",
            related_user=user_context
        )