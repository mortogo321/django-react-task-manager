"""Shared pytest fixtures."""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from tasks.models import Task
from workers.models import Employer, Worker


@pytest.fixture
def employer(db):
    return Employer.objects.create(
        first_name="Test",
        last_name="Owner",
        email="owner@example.com",
        plan="home",  # 3 worker limit
    )


@pytest.fixture
def other_employer(db):
    return Employer.objects.create(
        first_name="Other",
        last_name="Owner",
        email="other@example.com",
        plan="home",
    )


@pytest.fixture
def worker(employer):
    return Worker.objects.create(
        first_name="Somchai",
        last_name="Jaidee",
        nickname="Chai",
        phone="+66891111111",
        role="maid",
        employer=employer,
        salary=18_000,
        start_date=date.today() - timedelta(days=30),
    )


@pytest.fixture
def task(employer, worker):
    return Task.objects.create(
        title="Clean kitchen",
        description="Wipe surfaces",
        employer=employer,
        worker=worker,
        status="created",
        priority="medium",
    )


@pytest.fixture
def api(employer):
    """API client authenticated as `employer`."""
    client = APIClient()
    client.credentials(
        HTTP_X_EMPLOYER_ID=str(employer.id),
        HTTP_X_USER_ROLE="employer",
    )
    return client


@pytest.fixture
def api_other(other_employer):
    """API client authenticated as `other_employer`."""
    client = APIClient()
    client.credentials(
        HTTP_X_EMPLOYER_ID=str(other_employer.id),
        HTTP_X_USER_ROLE="employer",
    )
    return client


@pytest.fixture
def api_anon():
    return APIClient()
