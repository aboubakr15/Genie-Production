import json
import redis
from django.conf import settings

r = redis.from_url(settings.REDIS_URL)

def get_progress(job_id):
    data = r.get(f"enrichment_progress:{job_id}")
    if data:
        return json.loads(data)
    return {
        'current_batch': 0,
        'total_batches': 0,
        'companies_processed': 0,
        'total_companies': 0,
        'current_phase': 'initial',
        'is_complete': False
    }

def set_progress(job_id, data):
    r.set(f"enrichment_progress:{job_id}", json.dumps(data), ex=80000)  # 22 hours expiry

def reset_progress(job_id):
    set_progress(job_id, {
        'current_batch': 0,
        'total_batches': 0,
        'companies_processed': 0,
        'total_companies': 0,
        'current_phase': 'initial',
        'is_complete': False
    })
