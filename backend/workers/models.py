"""Models for employers and household workers."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# Single source of truth for plans (limit + monthly THB price).
PLANS = {
    "free": {"label": "Free", "worker_limit": 1, "price_thb": 0},
    "home": {"label": "Home", "worker_limit": 3, "price_thb": 599},
    "management": {"label": "Management", "worker_limit": 10, "price_thb": 1199},
    "corporate": {"label": "Corporate", "worker_limit": 999, "price_thb": 4999},
}


class Employer(models.Model):
    """Employer (expat / homeowner) who hires household staff."""

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("ru", "Russian"),
        ("zh", "Chinese"),
        ("ja", "Japanese"),
        ("ko", "Korean"),
        ("fr", "French"),
        ("de", "German"),
        ("th", "Thai"),
    ]
    PLAN_CHOICES = [(k, v["label"]) for k, v in PLANS.items()]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def worker_limit(self) -> int:
        return PLANS.get(self.plan, PLANS["free"])["worker_limit"]

    @property
    def plan_price_thb(self) -> int:
        return PLANS.get(self.plan, PLANS["free"])["price_thb"]

    def assert_can_add_worker(self, *, exclude_pk: int | None = None) -> None:
        """
        Raise ValidationError if adding (or activating) one more worker
        would exceed the plan's `worker_limit`. Caller must already hold
        a row-level lock if running concurrently — see
        `Employer.lock_for_update()`.
        """
        qs = self.workers.filter(is_active=True)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if qs.count() >= self.worker_limit:
            raise ValidationError(
                f"Employer has reached the worker limit for the "
                f"'{self.plan}' plan ({self.worker_limit} workers)."
            )

    @classmethod
    def lock_for_update(cls, pk: int) -> "Employer":
        """Re-fetch the employer row with `SELECT … FOR UPDATE`."""
        return cls.objects.select_for_update().get(pk=pk)


class Worker(models.Model):
    """Household staff member (maid, nanny, driver, cook, gardener)."""

    ROLE_CHOICES = [
        ("maid", "Maid / Housekeeper"),
        ("nanny", "Nanny / Babysitter"),
        ("driver", "Driver"),
        ("cook", "Cook / Chef"),
        ("gardener", "Gardener"),
        ("guard", "Security Guard"),
        ("other", "Other"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50, blank=True, help_text="Thai nickname")
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="workers")
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Monthly salary in THB",
    )
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # `created_at` is locale-stable; `first_name` order is meaningless
        # for Thai/Latin mixed names.
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employer", "is_active"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        display = self.nickname if self.nickname else self.first_name
        return f"{display} ({self.get_role_display()})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
