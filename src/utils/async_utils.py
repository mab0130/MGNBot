"""
Async and Concurrent Utilities
"""

import asyncio
import logging
from typing import List, Callable, Any, TypeVar, Awaitable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        
    async def acquire(self):
        """Acquire permission to make a call"""
        now = time.time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # If we've made too many calls, wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.acquire()
        
        # Add current call
        self.calls.append(time.time())
        
    def reset(self):
        """Reset the rate limiter"""
        self.calls.clear()


async def run_concurrent_with_rate_limit(
    func: Callable[[T], R],
    items: List[T],
    max_concurrent: int = 10,
    rate_limit: Optional[RateLimiter] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[R]:
    """
    Run a function concurrently on a list of items with rate limiting
    
    Args:
        func: Function to run on each item
        items: List of items to process
        max_concurrent: Maximum number of concurrent operations
        rate_limit: Optional rate limiter
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of results in the same order as input items
    """
    results = [None] * len(items)
    completed = 0
    
    async def process_item(index: int, item: T) -> tuple[int, R]:
        """Process a single item"""
        nonlocal completed
        
        if rate_limit:
            await rate_limit.acquire()
            
        try:
            result = await asyncio.get_event_loop().run_in_executor(None, func, item)
            return index, result
        except Exception as e:
            logger.error(f"Error processing item {index}: {e}")
            raise
        finally:
            completed += 1
            if progress_callback:
                progress_callback(completed, len(items))
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(index: int, item: T) -> tuple[int, R]:
        """Process item with semaphore"""
        async with semaphore:
            return await process_item(index, item)
    
    # Create tasks
    tasks = [
        process_with_semaphore(i, item)
        for i, item in enumerate(items)
    ]
    
    # Wait for all tasks to complete
    for task in asyncio.as_completed(tasks):
        try:
            index, result = await task
            results[index] = result
        except Exception as e:
            logger.error(f"Task failed: {e}")
            # Find the failed task and mark it as failed
            for i, item in enumerate(items):
                if results[i] is None:
                    results[i] = e
                    break
    
    return results


def run_concurrent_sync(
    func: Callable[[T], R],
    items: List[T],
    max_workers: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[R]:
    """
    Run a function concurrently using ThreadPoolExecutor
    
    Args:
        func: Function to run on each item
        items: List of items to process
        max_workers: Maximum number of worker threads
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of results in the same order as input items
    """
    results = [None] * len(items)
    completed = 0
    
    def process_item(index: int, item: T) -> tuple[int, R]:
        """Process a single item"""
        nonlocal completed
        
        try:
            result = func(item)
            return index, result
        except Exception as e:
            logger.error(f"Error processing item {index}: {e}")
            raise
        finally:
            completed += 1
            if progress_callback:
                progress_callback(completed, len(items))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_item, i, item): i
            for i, item in enumerate(items)
        }
        
        # Collect results
        for future in as_completed(future_to_index):
            try:
                index, result = future.result()
                results[index] = result
            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Mark the failed task
                index = future_to_index[future]
                results[index] = e
    
    return results


class BulkOperationManager:
    """Manager for bulk operations with progress tracking"""
    
    def __init__(self, max_concurrent: int = 10, rate_limit_calls: int = 50, rate_limit_window: float = 60.0):
        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_window)
        
    async def execute_bulk_operation(
        self,
        operation_func: Callable[[T], R],
        items: List[T],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[R]:
        """
        Execute a bulk operation with rate limiting and progress tracking
        
        Args:
            operation_func: Function to execute on each item
            items: List of items to process
            progress_callback: Optional progress callback
            
        Returns:
            List of results
        """
        logger.info(f"Starting bulk operation on {len(items)} items with max {self.max_concurrent} concurrent")
        
        start_time = time.time()
        results = await run_concurrent_with_rate_limit(
            operation_func,
            items,
            max_concurrent=self.max_concurrent,
            rate_limit=self.rate_limiter,
            progress_callback=progress_callback
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Count successes and failures
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = len(results) - successes
        
        logger.info(f"Bulk operation completed in {duration:.2f}s: {successes} success, {failures} failed")
        
        return results 