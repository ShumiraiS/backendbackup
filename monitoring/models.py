from django.db import models

class BaseReading(models.Model):
    site_id = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(db_index=True)

    temperature = models.FloatField(null=True, blank=True)
    ph = models.FloatField(null=True, blank=True)
    cod = models.FloatField(null=True, blank=True)
    chlorides = models.FloatField(null=True, blank=True)
    suspended_solids = models.FloatField(null=True, blank=True)

    source = models.CharField(max_length=30, default="sim")  # sim | sensor | hybrid
    compliance = models.CharField(max_length=20, default="UNKNOWN")  # GREEN/AMBER/RED/OFFLINE
    anomaly_flag = models.BooleanField(default=False)
    deviation_score = models.FloatField(default=0.0)

    class Meta:
        abstract = True
        ordering = ["-timestamp"]

class IndustryReading(BaseReading):
    pass

class STPReading(BaseReading):
    pass

# Create your models here.
