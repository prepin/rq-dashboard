import json
import time
import unittest

import redis
from rq import Queue, Worker, pop_connection, push_connection

from rq_dashboard.cli import make_flask_app
from rq_dashboard.web import escape_format_instance_list


HTTP_OK = 200

class BasicTestCase(unittest.TestCase):
    redis_client = None

    def get_redis_client(self):
        if self.redis_client is None:
            self.redis_client = redis.Redis()
        return self.redis_client

    def setUp(self):
        self.app = make_flask_app(None, None, None, '')
        self.app.testing = True
        self.app.config['RQ_DASHBOARD_REDIS_URL'] = ['redis://127.0.0.1']
        self.app.redis_conn = self.get_redis_client()
        push_connection(self.get_redis_client())
        self.client = self.app.test_client()

    def tearDown(self):
        q = Queue(connection=self.app.redis_conn)
        q.empty()
        pop_connection()

    def test_dashboard_ok(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, HTTP_OK)

    def test_queues_list_json(self):
        response = self.client.get('/0/data/queues.json')
        self.assertEqual(response.status_code, HTTP_OK)
        data = json.loads(response.data.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertIn('queues', data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_workers_list_json(self):
        response = self.client.get('/0/data/workers.json')
        self.assertEqual(response.status_code, HTTP_OK)
        data = json.loads(response.data.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertIn('workers', data)

    def test_queued_jobs_list(self):
        response_dashboard = self.client.get('/0/view/jobs')
        self.assertEqual(response_dashboard.status_code, HTTP_OK)
        response_queued = self.client.get('/0/view/jobs/default/queued/8/asc/1')
        self.assertEqual(response_queued.status_code, HTTP_OK)
        response = self.client.get('/0/data/jobs/default/queued/8/asc/1.json')
        self.assertEqual(response.status_code, HTTP_OK)
        data = json.loads(response.data.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertIn('jobs', data)

    def test_single_job_view(self):
        def some_work():
            return
        q = Queue(connection=self.app.redis_conn)
        job = q.enqueue(some_work)
        job_url = '/0/view/job/' + job.id
        response = self.client.get(job_url)
        self.assertEqual(response.status_code, HTTP_OK)
        job.delete()

    def test_del_job_mechanism(self):
        def some_work():
            return
        q = Queue(connection=self.app.redis_conn)
        job = q.enqueue(some_work)
        job_del_url = '/job/' + job.id + '/delete'
        response_del = self.client.post(job_del_url)
        self.assertEqual(response_del.status_code, HTTP_OK)

    def test_registry_jobs_list(self):
        response = self.client.get('/0/data/jobs/default/failed/8/asc/1.json')
        self.assertEqual(response.status_code, HTTP_OK)
        data = json.loads(response.data.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertIn('jobs', data)

    def test_worker_python_version_field(self):
        w = Worker(['q'])
        w.register_birth()
        response = self.client.get('/0/data/workers.json')
        data = json.loads(response.data.decode('utf8'))
        if getattr(w, 'python_version', None):
            self.assertEqual(w.python_version, data['workers'][0]['python_version'])
        else:
            self.assertEqual('', data['workers'][0]['python_version'])
        w.register_death()

    def test_worker_version_field(self):
        w = Worker(['q'])
        w.register_birth()
        response = self.client.get('/0/data/workers.json')
        data = json.loads(response.data.decode('utf8'))
        if getattr(w, 'version', None):
            self.assertEqual(w.version, data['workers'][0]['version'])
        else:
            self.assertEqual('', data['workers'][0]['version'])
        w.register_death()


    def test_instance_escaping(self):
        expected_redis_instance = "redis://***:***@redis.example.com:6379"
        self.assertEqual(
            escape_format_instance_list(
                [
                    "redis://myuser:secretpassword@redis.example.com:6379",
                    "redis://:secretpassword@redis.example.com:6379",
                    "redis://:@redis.example.com:6379",
                ]
            ),
            [expected_redis_instance, expected_redis_instance, expected_redis_instance],
        )
    
    def test_job_sort_order(self):
        def some_work():
            return
        q = Queue(connection=self.app.redis_conn)
        job_ids = []
        for _ in range(3):
            job = q.enqueue(some_work)
            job_ids.append(job.id)
            time.sleep(2)

        response_asc = self.client.get('/0/data/jobs/default/queued/3/asc/1.json')
        self.assertEqual(response_asc.status_code, HTTP_OK)
        data_asc = json.loads(response_asc.data.decode('utf8'))
        self.assertEqual(job_ids, [job['id'] for job in data_asc['jobs']])

        response_dsc = self.client.get('/0/data/jobs/default/queued/10/dsc/1.json')
        self.assertEqual(response_dsc.status_code, HTTP_OK)
        data_dsc = json.loads(response_dsc.data.decode('utf8'))
        self.assertEqual(job_ids[::-1], [job['id'] for job in data_dsc['jobs']])


__all__ = [
    'BasicTestCase',
]