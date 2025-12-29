"""
Load Testing with Locust.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import os
import random
import time


class GatewayUser(HttpUser):
    """Simulates a typical gateway user."""

    wait_time = between(0.5, 2)

    def on_start(self):
        """Setup before running tasks."""
        self.api_key = os.environ.get("API_KEY", "gw_test_key_placeholder")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self.models = ["mock-gpt", "test-model"]
        self.features = ["chat-support", "document-summary", "code-review"]

    @task(10)
    def chat_completion(self):
        """Test chat completion endpoint."""
        payload = {
            "model": random.choice(self.models),
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"Hello! Tell me about {random.choice(['Python', 'APIs', 'testing', 'performance'])}",
                },
            ],
            "max_tokens": random.randint(100, 500),
            "feature_id": random.choice(self.features),
        }

        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success()  # Rate limit is expected under load
            else:
                response.failure(f"Status: {response.status_code}")

    @task(3)
    def chat_with_dry_run(self):
        """Test dry-run mode."""
        payload = {
            "model": random.choice(self.models),
            "messages": [
                {"role": "user", "content": "Test message for dry run"},
            ],
        }

        headers = {**self.headers, "X-Dry-Run": "true"}

        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("dry_run"):
                    response.success()
                else:
                    response.failure("Expected dry_run response")
            else:
                response.failure(f"Status: {response.status_code}")

    @task(2)
    def health_check(self):
        """Test health endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def get_applications(self):
        """Test admin applications endpoint."""
        with self.client.get(
            "/admin/applications",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def get_budgets(self):
        """Test admin budgets endpoint."""
        with self.client.get(
            "/admin/budgets",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def get_plans(self):
        """Test plans endpoint."""
        with self.client.get(
            "/admin/plans/",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


class HighVolumeUser(HttpUser):
    """Simulates high-volume API consumer."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.api_key = os.environ.get("API_KEY", "gw_test_key_placeholder")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @task
    def rapid_chat(self):
        """Rapid fire chat requests."""
        payload = {
            "model": "mock-gpt",
            "messages": [
                {"role": "user", "content": "Quick test"},
            ],
            "max_tokens": 50,
        }

        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers,
        )


class BurstUser(HttpUser):
    """Simulates bursty traffic patterns."""

    wait_time = between(0.01, 0.1)

    def on_start(self):
        self.api_key = os.environ.get("API_KEY", "gw_test_key_placeholder")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self.burst_count = 0

    @task
    def burst_requests(self):
        """Send burst of requests."""
        self.burst_count += 1

        # Send 10 requests in quick succession
        if self.burst_count % 10 == 0:
            time.sleep(random.uniform(1, 3))  # Pause between bursts

        payload = {
            "model": "mock-gpt",
            "messages": [
                {"role": "user", "content": f"Burst request {self.burst_count}"},
            ],
        }

        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers,
        )


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("LLM Gateway Load Test Starting")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("LLM Gateway Load Test Complete")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        print(f"Request failed: {name} - {exception}")
