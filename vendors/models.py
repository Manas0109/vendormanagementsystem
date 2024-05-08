import uuid
from typing import Union
from orders.constants import OrderStatus
from vendors.utils import get_random_code
from django.db import models
from django.utils.translation import gettext as _
from django.urls import reverse


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Vendor(BaseModel):
    name = models.CharField(max_length=255)
    contact_details = models.TextField()
    address = models.TextField()
    vendor_code = models.CharField(
        max_length=50, unique=True, default=get_random_code, editable=False
    )
    on_time_delivery_rate = models.FloatField(default=0.0)
    quality_rating_avg = models.FloatField(default=0.0)
    average_response_time = models.FloatField(default=0.0)
    fulfillment_rate = models.FloatField(default=0.0)

    class Meta:
        verbose_name = _("vendor")
        verbose_name_plural = _("vendors")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("vendors:vendor-actions", kwargs={"pk": self.pk})

    def get_purchase_orders_by_status(self, status=Union[OrderStatus, str] | None
    ) -> models.QuerySet | None:
        if status is None:
            return self.purchase_orders.all()
        elif OrderStatus.is_valid_status(status=status):
            return self.purchase_orders.filter(status=status)
        else:
            return None

    def calc_on_time_delivery_rate(self) -> float:
        """
        Count the number of completed POs delivered on or before delivery_date 
        and divide by the total number of completed POs for that vendor.
        """
        po_data = self.get_purchase_orders_by_status(status=OrderStatus.COMPLETED)
        filter_on_time_deliverables = po_data.filter(
            acknowledgment_date__lte=models.F("delivery_date")
        )
        try:
            return round(filter_on_time_deliverables.count() / po_data.count(), 2)
        except ZeroDivisionError:
            return 0

    def calc_avg_quality_ratings(self):
        """
        Calculate the average of all quality_rating values for completed POs of the vendor.
        """
        po_data = self.get_purchase_orders_by_status(status=OrderStatus.COMPLETED)
        result = po_data.aggregate(
            avg_quality_rating=models.Avg("quality_rating", default=0.0)
        )
        return round(result.get("avg_quality_rating"))

    def calc_fulfillment_rate(self):
        """
        The function calculates the fulfillment rate by dividing the number of completed purchase orders
        by the total number of purchase orders
        """
        po_list_status_completed = self.get_purchase_orders_by_status(
            status=OrderStatus.COMPLETED
        )
        po_list = self.get_purchase_orders_by_status(status=None)
        try:
            return round(po_list_status_completed.count() / po_list.count(), 2)
        except ZeroDivisionError:
            return 0

    def calc_avg_response_time(self):
        """
        Compute the time difference between issue_date and acknowledgment_date 
        for each PO, and then find the average of these times for all POs of the vendor.
        """
        filter_po_data = self.purchase_orders.filter(
            issue_date__isnull=False, acknowledgment_date__isnull=False
        )

        if filter_po_data.exists():
            result = filter_po_data.aggregate(
                avg_response_time=models.Avg(
                    models.F("acknowledgment_date") - models.F("issue_date")
                )
            )
            return round(result.get("avg_response_time").total_seconds(), 2)
        return 0


class HistoricalPerformance(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    history_date = models.DateTimeField(
        auto_now_add=True
    )  
    on_time_delivery_rate = models.FloatField()
    quality_rating_avg = models.FloatField()
    average_response_time = models.FloatField()
    fulfillment_rate = models.FloatField()

    def __str__(self):
        return f"{self.vendor.name} - {self.history_date}"

    class Meta:
        ordering = ["-history_date"]
        verbose_name = "Historical Performance"
        verbose_name_plural = "Historical Performances"


