from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    Wallet, WalletTransaction, School, Student
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError
)

class FinanceService:
    """
    Handles business logic for financial transactions, including wallet operations,
    payment validation, and fee/fine management.
    """

    TRANSACTION_TYPES = {
        'CREDIT': WalletTransaction.TRANSACTION_TYPE_CREDIT,
        'DEBIT': WalletTransaction.TRANSACTION_TYPE_DEBIT
    }

    
    @staticmethod
    def _process_external_payment(amount: float, gateway_data: dict) -> str:
        """
        [PLACEHOLDER] Simulates/initiates communication with an external provider (e.g., Razorpay, Stripe).
        
        In a real production environment, this would involve:
        1. Calling the payment gateway's API.
        2. Verifying the payment status (e.g., successful, pending, failed).
        3. Returning a unique transaction ID (Razorpay ID).
        """
        
        if not gateway_data.get('transaction_id'):
            raise BusinessRuleViolation("External payment gateway verification failed (Missing Transaction ID).")
        if amount <= 0:
            raise ValidationError("Payment amount must be positive.")
        

        
        return gateway_data['transaction_id'] 

    
    
    @staticmethod
    def _get_wallet_by_student(student_id: int) -> Wallet:
        """Retrieves or creates the wallet for a given student."""
        student = get_object_or_404(Student, pk=student_id)
        
        wallet, created = Wallet.objects.get_or_create(
            student=student, 
            school=student.school,
            defaults={'balance': 0.00}
        )
        return wallet

    

    @classmethod
    @transaction.atomic
    def process_wallet_top_up(
        cls, 
        student_id: int, 
        amount: float, 
        payment_method: str, 
        gateway_data: dict
    ) -> WalletTransaction:
        """
        Processes an external payment (top-up) and credits the student's wallet.
        Enforces payment validity rules.
        """
        if amount <= 0:
            raise ValidationError("Top-up amount must be positive.")
            
        
        external_id = cls._process_external_payment(amount, gateway_data)
        
        
        if WalletTransaction.objects.filter(external_transaction_id=external_id).exists():
            raise DuplicateEntryError(f"Payment {external_id} has already been processed.")

        
        wallet = cls._get_wallet_by_student(student_id)

        
        wallet.balance += amount
        wallet.save(update_fields=['balance'])

        
        transaction_record = WalletTransaction.objects.create(
            wallet=wallet,
            school=wallet.school,
            transaction_type=cls.TRANSACTION_TYPES['CREDIT'],
            amount=amount,
            current_balance=wallet.balance,
            description=f"Top-up via {payment_method}",
            external_transaction_id=external_id
        )

        return transaction_record

    @classmethod
    @transaction.atomic
    def process_canteen_purchase(cls, student_id: int, purchase_amount: float, item_id: int) -> WalletTransaction:
        """
        Debits the student's wallet for a canteen purchase.
        Enforces inventory stock constraints (conceptually).
        """
        if purchase_amount <= 0:
            raise ValidationError("Purchase amount must be positive.")

        
        wallet = cls._get_wallet_by_student(student_id)

        
        
        
        
        
        
        if wallet.balance < purchase_amount:
            raise BusinessRuleViolation(
                f"Insufficient funds. Wallet balance: {wallet.balance}, Required: {purchase_amount}"
            )

        
        wallet.balance -= purchase_amount
        wallet.save(update_fields=['balance'])

        
        transaction_record = WalletTransaction.objects.create(
            wallet=wallet,
            school=wallet.school,
            transaction_type=cls.TRANSACTION_TYPES['DEBIT'],
            amount=purchase_amount,
            current_balance=wallet.balance,
            description="Canteen purchase"
        )
        
        
        

        return transaction_record
