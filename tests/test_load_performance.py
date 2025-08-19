"""
Load Testing and Performance Benchmarking for Project Archangel
Tests system performance under various load conditions
"""

import asyncio
import aiohttp
import time
import statistics
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoadTestResult:
    """Container for load test results"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.error_types = {}
        self.start_time = None
        self.end_time = None
        
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.quantiles(self.response_times, n=20)[18]  # 95th percentile
    
    @property
    def requests_per_second(self) -> float:
        if not self.start_time or not self.end_time:
            return 0.0
        duration = (self.end_time - self.start_time).total_seconds()
        return self.total_requests / duration if duration > 0 else 0.0
    
    def add_result(self, success: bool, response_time: float, error_type: str = None):
        """Add a single request result"""
        self.total_requests += 1
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1


class ProjectArchangelLoadTester:
    """Load tester for Project Archangel API"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def generate_task_data(self, client_id: int = None) -> Dict[str, Any]:
        """Generate random task data for testing"""
        now = datetime.now(timezone.utc)
        client_id = client_id or random.randint(1, 10)
        
        task_types = ["bugfix", "feature", "enhancement", "maintenance", "hotfix"]
        priorities = [1, 2, 3, 4, 5]
        
        return {
            "title": f"Load Test Task {random.randint(1000, 9999)}",
            "description": f"Generated task for load testing - {random.choice(task_types)}",
            "client": f"client-{client_id}",
            "importance": random.choice(priorities),
            "effort_hours": round(random.uniform(0.5, 16.0), 1),
            "deadline": (now + timedelta(hours=random.randint(1, 168))).isoformat(),
            "labels": [random.choice(task_types), "load-test"],
            "task_type": random.choice(task_types),
            "project": f"project-{random.randint(1, 5)}"
        }
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> tuple:
        """Make a single HTTP request and measure timing"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                async with self.session.get(url) as response:
                    response_time = time.time() - start_time
                    return response.status == 200, response_time, response.status
            
            elif method.upper() == "POST":
                async with self.session.post(url, json=data) as response:
                    response_time = time.time() - start_time
                    return response.status in [200, 201], response_time, response.status
            
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data) as response:
                    response_time = time.time() - start_time
                    return response.status == 200, response_time, response.status
                    
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return False, response_time, "timeout"
        except Exception as e:
            response_time = time.time() - start_time
            return False, response_time, str(type(e).__name__)
    
    async def health_check_load_test(self, num_requests: int = 100, concurrency: int = 10) -> LoadTestResult:
        """Load test the health check endpoint"""
        logger.info(f"Starting health check load test: {num_requests} requests, {concurrency} concurrent")
        
        result = LoadTestResult()
        result.start_time = datetime.now()
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def single_health_request():
            async with semaphore:
                success, response_time, status = await self.make_request("GET", "/health")
                result.add_result(success, response_time, str(status) if not success else None)
        
        # Execute requests concurrently
        tasks = [single_health_request() for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        
        result.end_time = datetime.now()
        return result
    
    async def task_creation_load_test(self, num_tasks: int = 50, concurrency: int = 5) -> LoadTestResult:
        """Load test task creation endpoints"""
        logger.info(f"Starting task creation load test: {num_tasks} tasks, {concurrency} concurrent")
        
        result = LoadTestResult()
        result.start_time = datetime.now()
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def create_single_task():
            async with semaphore:
                task_data = self.generate_task_data()
                success, response_time, status = await self.make_request("POST", "/api/tasks", task_data)
                result.add_result(success, response_time, str(status) if not success else None)
        
        tasks = [create_single_task() for _ in range(num_tasks)]
        await asyncio.gather(*tasks)
        
        result.end_time = datetime.now()
        return result
    
    async def task_listing_load_test(self, num_requests: int = 100, concurrency: int = 10) -> LoadTestResult:
        """Load test task listing with various filters"""
        logger.info(f"Starting task listing load test: {num_requests} requests, {concurrency} concurrent")
        
        result = LoadTestResult()
        result.start_time = datetime.now()
        
        semaphore = asyncio.Semaphore(concurrency)
        
        # Various query patterns
        query_patterns = [
            "/api/tasks",
            "/api/tasks?limit=10",
            "/api/tasks?client=client-1",
            "/api/tasks?status=triaged",
            "/api/tasks?importance=4",
            "/api/tasks?page=1&limit=20"
        ]
        
        async def single_listing_request():
            async with semaphore:
                endpoint = random.choice(query_patterns)
                success, response_time, status = await self.make_request("GET", endpoint)
                result.add_result(success, response_time, str(status) if not success else None)
        
        tasks = [single_listing_request() for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        
        result.end_time = datetime.now()
        return result
    
    async def scoring_algorithm_load_test(self, num_requests: int = 200, concurrency: int = 15) -> LoadTestResult:
        """Load test the enhanced scoring algorithm"""
        logger.info(f"Starting scoring algorithm load test: {num_requests} requests, {concurrency} concurrent")
        
        result = LoadTestResult()
        result.start_time = datetime.now()
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def single_scoring_request():
            async with semaphore:
                task_data = self.generate_task_data()
                success, response_time, status = await self.make_request("POST", "/api/tasks/score", task_data)
                result.add_result(success, response_time, str(status) if not success else None)
        
        tasks = [single_scoring_request() for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        
        result.end_time = datetime.now()
        return result
    
    async def mixed_workload_test(self, duration_seconds: int = 60, requests_per_second: int = 10) -> LoadTestResult:
        """Simulate realistic mixed workload"""
        logger.info(f"Starting mixed workload test: {duration_seconds}s duration, {requests_per_second} RPS target")
        
        result = LoadTestResult()
        result.start_time = datetime.now()
        
        # Define workload distribution
        workload_distribution = [
            ("GET", "/health", None, 0.2),                    # 20% health checks
            ("GET", "/api/tasks", None, 0.3),                 # 30% task listing
            ("POST", "/api/tasks", "task_data", 0.25),        # 25% task creation
            ("POST", "/api/tasks/score", "task_data", 0.15),  # 15% scoring
            ("GET", "/api/analytics/performance", None, 0.1)   # 10% analytics
        ]
        
        async def generate_request():
            method, endpoint, data_type, _ = random.choices(
                workload_distribution, 
                weights=[w[3] for w in workload_distribution]
            )[0]
            
            data = None
            if data_type == "task_data":
                data = self.generate_task_data()
            
            success, response_time, status = await self.make_request(method, endpoint, data)
            result.add_result(success, response_time, str(status) if not success else None)
        
        # Generate requests at target rate
        end_time = time.time() + duration_seconds
        1.0 / requests_per_second
        
        while time.time() < end_time:
            batch_start = time.time()
            
            # Create batch of requests
            batch_size = min(requests_per_second, int((end_time - time.time()) * requests_per_second))
            if batch_size <= 0:
                break
                
            tasks = [generate_request() for _ in range(batch_size)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for next batch
            batch_duration = time.time() - batch_start
            sleep_time = max(0, 1.0 - batch_duration)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        result.end_time = datetime.now()
        return result


class PerformanceBenchmark:
    """Performance benchmarking suite"""
    
    @staticmethod
    async def run_comprehensive_load_test(base_url: str = "http://localhost:8080") -> Dict[str, LoadTestResult]:
        """Run comprehensive load testing suite"""
        logger.info("🚀 Starting Comprehensive Load Testing Suite")
        logger.info("=" * 60)
        
        results = {}
        
        async with ProjectArchangelLoadTester(base_url) as tester:
            # Test 1: Health Check Load Test
            logger.info("\n📊 Test 1: Health Check Load Test")
            results["health_check"] = await tester.health_check_load_test(
                num_requests=200, concurrency=20
            )
            
            # Test 2: Task Creation Load Test
            logger.info("\n📝 Test 2: Task Creation Load Test")
            results["task_creation"] = await tester.task_creation_load_test(
                num_tasks=100, concurrency=10
            )
            
            # Test 3: Task Listing Load Test
            logger.info("\n📋 Test 3: Task Listing Load Test")
            results["task_listing"] = await tester.task_listing_load_test(
                num_requests=150, concurrency=15
            )
            
            # Test 4: Scoring Algorithm Load Test
            logger.info("\n🧮 Test 4: Scoring Algorithm Load Test")
            results["scoring"] = await tester.scoring_algorithm_load_test(
                num_requests=300, concurrency=20
            )
            
            # Test 5: Mixed Workload Test
            logger.info("\n🔀 Test 5: Mixed Workload Test")
            results["mixed_workload"] = await tester.mixed_workload_test(
                duration_seconds=30, requests_per_second=15
            )
        
        return results
    
    @staticmethod
    def print_test_results(results: Dict[str, LoadTestResult]):
        """Print formatted test results"""
        print("\n" + "=" * 80)
        print("📊 LOAD TESTING RESULTS")
        print("=" * 80)
        
        for test_name, result in results.items():
            print(f"\n🔍 {test_name.replace('_', ' ').title()}")
            print("-" * 50)
            print(f"Total Requests:     {result.total_requests:,}")
            print(f"Successful:         {result.successful_requests:,} ({result.success_rate:.1f}%)")
            print(f"Failed:             {result.failed_requests:,}")
            print(f"Average Response:   {result.avg_response_time:.3f}s")
            print(f"95th Percentile:    {result.p95_response_time:.3f}s")
            print(f"Requests/Second:    {result.requests_per_second:.1f}")
            
            if result.error_types:
                print(f"Error Types:        {dict(result.error_types)}")
        
        # Overall summary
        print("\n" + "=" * 80)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 80)
        
        total_requests = sum(r.total_requests for r in results.values())
        total_successful = sum(r.successful_requests for r in results.values())
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_times = [r.avg_response_time for r in results.values()]
        overall_avg_response = statistics.mean(avg_response_times) if avg_response_times else 0
        
        print(f"Total Requests:       {total_requests:,}")
        print(f"Overall Success Rate: {overall_success_rate:.1f}%")
        print(f"Average Response:     {overall_avg_response:.3f}s")
        
        # Performance assessment
        print("\n🎯 PERFORMANCE ASSESSMENT:")
        if overall_success_rate >= 95 and overall_avg_response <= 0.5:
            print("✅ EXCELLENT - System performs well under load")
        elif overall_success_rate >= 90 and overall_avg_response <= 1.0:
            print("✅ GOOD - System handles load adequately")
        elif overall_success_rate >= 80 and overall_avg_response <= 2.0:
            print("⚠️  ACCEPTABLE - Some performance issues under load")
        else:
            print("❌ NEEDS IMPROVEMENT - Significant performance issues")
    
    @staticmethod
    def generate_performance_report(results: Dict[str, LoadTestResult]) -> str:
        """Generate detailed performance report"""
        report = []
        report.append("# Project Archangel - Load Testing Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for test_name, result in results.items():
            report.append(f"## {test_name.replace('_', ' ').title()}")
            report.append("")
            report.append(f"- **Total Requests**: {result.total_requests:,}")
            report.append(f"- **Success Rate**: {result.success_rate:.1f}%")
            report.append(f"- **Average Response Time**: {result.avg_response_time:.3f}s")
            report.append(f"- **95th Percentile**: {result.p95_response_time:.3f}s")
            report.append(f"- **Throughput**: {result.requests_per_second:.1f} requests/second")
            
            if result.error_types:
                report.append(f"- **Errors**: {dict(result.error_types)}")
            
            report.append("")
        
        return "\n".join(report)


# Main execution
async def main():
    """Run the complete load testing suite"""
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/health", timeout=5) as response:
                if response.status != 200:
                    logger.error("❌ API not responding at http://localhost:8080")
                    return
    except Exception as e:
        logger.error(f"❌ Cannot connect to API: {e}")
        logger.info("💡 Make sure Project Archangel is running: docker compose up -d")
        return
    
    # Run load tests
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_comprehensive_load_test()
    
    # Print results
    benchmark.print_test_results(results)
    
    # Save report
    report = benchmark.generate_performance_report(results)
    with open("load_test_report.md", "w") as f:
        f.write(report)
    
    logger.info("\n📄 Detailed report saved to: load_test_report.md")


if __name__ == "__main__":
    asyncio.run(main())