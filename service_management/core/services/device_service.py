from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import ReaderDevice, CollectorNode, DeviceErrorLog, School
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError,
    DuplicateEntryError
)

class DeviceService:
    """
    Handles business logic for managing Reader Devices and Collector Nodes, 
    including registration, status updates, and error logging.
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @staticmethod
    def _validate_mac_address(mac_address: str):
        """Ensures the MAC address is in a standard format (e.g., AA:BB:CC:DD:EE:FF)."""
       
        if len(mac_address) not in [12, 17] or ':' not in mac_address:
            raise ValidationError(f"MAC address '{mac_address}' is not in a recognized format.")

    

    @classmethod
    @transaction.atomic
    def register_reader_device(cls, school_id: int, mac_address: str, location_type: str, description: str = None) -> ReaderDevice:

        school = cls._validate_school_context(school_id)
        cls._validate_mac_address(mac_address)
        

        if ReaderDevice.objects.filter(school=school, mac_address=mac_address).exists():
            raise DuplicateEntryError(f"Reader device with MAC address {mac_address} already registered in this school.")


        valid_locations = dict(ReaderDevice.LOCATION_CHOICES).keys()
        if location_type not in valid_locations:
             raise ValidationError(f"Invalid location type '{location_type}'. Must be one of {', '.join(valid_locations)}")


        device = ReaderDevice.objects.create(
            school=school,
            mac_address=mac_address,
            location_type=location_type,
            description=description,
            is_active=True,
            last_ping_time=datetime.now() 
        )
        return device

    @classmethod
    @transaction.atomic
    def update_reader_status(cls, mac_address: str, school_id: int, status_data: dict) -> ReaderDevice:
        """
        Updates the operational status, battery, or firmware of an existing reader device.
        """
        school = cls._validate_school_context(school_id)
        
        
        device = get_object_or_404(ReaderDevice, mac_address=mac_address, school=school)

        
        if 'is_active' in status_data:
            device.is_active = status_data['is_active']
        if 'battery_level' in status_data:
            if not 0 <= status_data['battery_level'] <= 100:
                 raise ValidationError("Battery level must be between 0 and 100.")
            device.battery_level = status_data['battery_level']
        
        device.last_ping_time = datetime.now()
        device.save()
        
        return device

    

    @classmethod
    @transaction.atomic
    def log_device_error(cls, school_id: int, mac_address: str, error_code: str, severity: str, message: str) -> DeviceErrorLog:
        """
        Records a specific error reported by a device or detected by the backend.
        """
        school = cls._validate_school_context(school_id)
        
        
        reader_device = ReaderDevice.objects.filter(mac_address=mac_address, school=school).first()
        collector_node = CollectorNode.objects.filter(mac_address=mac_address, school=school).first()

        
        valid_severities = dict(DeviceErrorLog.SEVERITY_CHOICES).keys()
        if severity not in valid_severities:
             raise ValidationError(f"Invalid severity '{severity}'. Must be one of {', '.join(valid_severities)}")

        
        error_log = DeviceErrorLog.objects.create(
            school=school,
            mac_address=mac_address,
            reader_device=reader_device,
            collector_node=collector_node,
            error_code=error_code,
            severity=severity,
            message=message
        )
        
        
        if severity == DeviceErrorLog.SEVERITY_CRITICAL and reader_device:
            reader_device.is_active = False
            reader_device.save(update_fields=['is_active'])
            
        return error_log

    

    @classmethod
    @transaction.atomic
    def register_collector_node(cls, school_id: int, mac_address: str, location: str) -> CollectorNode:
        """
        Registers a main Collector Node (often a gateway for multiple readers).
        """
        school = cls._validate_school_context(school_id)
        cls._validate_mac_address(mac_address)
        
        
        if CollectorNode.objects.filter(school=school, mac_address=mac_address).exists():
            raise DuplicateEntryError(f"Collector Node with MAC address {mac_address} already registered.")

        
        node = CollectorNode.objects.create(
            school=school,
            mac_address=mac_address,
            location=location,
            is_active=True
        )
        return node
