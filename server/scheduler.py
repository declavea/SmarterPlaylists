import sys
import redis
import program_manager
import time
import simplejson as json
import threading
from datetime import datetime,date

class Scheduler(object):
    '''
        constraints - only one scheduled task per item
        squeue - a zset with proc IDs ('process:pid') sorted by excution times
        proces info a hash with
           pid, next exec time, 
            delta, count, error count, consecutive errors count

        process-stats: a list of json results, trimmed to size 10
        sleeper queue
    '''
    def __init__(self, redis, pm):
        self.r = redis
        self.pm = pm
        self.job_queue = 'sched-job-queue'
        self.proc_queue = 'sched-proc-queue'
        self.wait_queue = 'sched-wait-queue'
        self.max_time = 1000000
        self.max_cerrors = 3
        self.max_retained_results = 5
        self.max_age_results = 40 * 24 * 60 * 60

    def schedule(self, auth_code, user, pid, when, delta, total):
        # as a pipleline
        # add schedule to process info hash
        # if count > 0
        #    add proc-id when to squeue
        #    hash proc info to hash (dec count)
        # post to sleeper queue

        skey = mk_sched_key('job', user, pid)
        pipe = self.r.pipeline()
        pipe.hset(skey, 'auth_code', auth_code)
        pipe.hset(skey, 'user', user)
        pipe.hset(skey, 'pid', pid)
        pipe.hset(skey, 'when', when)
        pipe.hset(skey, 'delta', delta)
        pipe.hset(skey, 'total', total)
        pipe.hset(skey, 'runs', 0)
        pipe.hset(skey, 'errors', 0)
        pipe.hset(skey, 'cerrors', 0)
        pipe.hset(skey, 'status', 'running')
        pipe.execute()
        self.post_job(skey, when)
        return True

    def get_batch_schedule_status(self, user, pids):
        pipe = self.r.pipeline()
        for pid in pids:
            jkey = mk_sched_key('job', user, pid)
            pipe.hgetall(jkey)
        ss = pipe.execute()
        out = {}

        for pid, s in zip(pids,ss):
            if 'pid' in s:
                ps  = self.prep_status(s)
                out[ s['pid' ]] = ps
            else:
                out[pid] = {}
        return out


    def prep_status(self, status):
        skip_fields = set(['auth_code'])
        int_fields = set(['cerrors', 'delta', 'errors', 'next_run',
            'runs', 'total', 'when'])

        out = {}
        for k, v in status.items():
            if k in skip_fields:
                continue
            if k in int_fields:
                v = int(v)
            out[k] = v
        return out
        
    def post_job(self, skey, when):
	dict ={}
	dict[skey]=when
        print 'posting', skey, 'to run in', when - time.time(), 'secs'
        pipe = self.r.pipeline()
        pipe.hset(skey, 'status', 'queued')
        pipe.hset(skey, 'next_run', when)
        pipe.zadd(self.job_queue, dict)
        pipe.lpush(self.wait_queue, 1)
        pipe.execute()
        self.pm.inc_global_counter("jobs_posted")

    def cancel(self, user, pid):
        skey = mk_sched_key('job', user, pid)
        self.r.zrem(self.job_queue, skey)
        pipe = self.r.pipeline()
        pipe.hset(skey, 'next_run', 0)
        pipe.hset(skey, 'status', 'stopped')
        pipe.execute()
        self.pm.inc_global_counter("jobs_canceled")
        return True

    def get_run_stats(self, user, pid):
        skey = mk_sched_key('job', user, pid)
        stats = self.r.hgetall(skey)
        return self.prep_status(stats)

    def get_recent_results(self, user, pid):
        rkey = mk_sched_key('results', user, pid)
        results = self.r.lrange(rkey, 0, self.max_retained_results - 1)
        out = []
        for js in results:
            out.append(json.loads(js))
        return out

    def get_next_item(self):
        now = self.now()
        items = self.r.zrange(self.job_queue, 0, 0, withscores=True, score_cast_func=int)
        if len(items) > 0:
            item = items[0]
            skey, next_time = item
            if now >= next_time:
                self.r.zrem(self.job_queue, skey)
                return skey
        else:
            return None

    def get_next_delta(self):
        now = self.now()
        items = self.r.zrange(self.job_queue, 0, 0, withscores=True, score_cast_func=int)
        if len(items) > 0:
            item = items[0]
            skey, next_time = item
            return next_time - now
        else:
            return self.max_time
        
    def wait_for_next(self):
        timeout = self.get_next_delta()
        if timeout > 0:
            print 'waiting for', timeout, 'secs'
            self.r.blpop(self.wait_queue, timeout)
        return self.get_next_item()
            
    def execute_job(self, skey):
        results = None
        info = self.r.hgetall(skey)
        print 'execute_job', skey, info
        if info:
            print 'execute_job', info
            auth_code = info['auth_code']
            pid = info['pid']
            results = self.pm.execute_program(auth_code, pid, True)
            self.pm.inc_global_counter("jobs_executed")
        return results

    def run_job(self, skey):
        self.r.hset(skey, 'status', 'running')
        results = self.execute_job(skey)
        if results:
            self.process_job_result(skey, results)

    def process_job_result(self, skey, results):
        p = self.r.pipeline()
        p.hincrby(skey, 'runs', 1)
        if results['status'] == 'ok':
            p.hset(skey, 'cerrors', 0)
        else:
            p.hincrby(skey, 'cerrors', 1)
            p.hincrby(skey, 'errors', 1)
        p.hgetall(skey)
        pres = p.execute()
        info = pres[-1]

        cerrors = int(info['cerrors'])
        runs = int(info['runs'])
        delta = int(info['delta'])

        print
        print 'info', info
        print

        user = info['user']
        pid = info['pid']

        results['runtime'] = time.time()
        if cerrors > self.max_cerrors:
            results['info'] = 'max consecutive errors exceeded, job cancelled'
            self.r.hset(skey, 'next_run', 0)
            self.r.hset(skey, 'status', 'cancelled')
            self.pm.inc_global_counter("jobs_max_errors_reached")
        elif runs >= int(info['total']):
            results['info'] = 'total runs reached, job finished'
            self.r.hset(skey, 'status', 'finished')
            self.r.hset(skey, 'next_run', 0)
            self.pm.inc_global_counter("jobs_total_runs_reached")
        elif delta == 0:
            results['info'] = 'run cancelled by user'
            self.r.hset(skey, 'status', 'cancelled')
            self.r.hset(skey, 'next_run', 0)
            self.pm.inc_global_counter("jobs_cancelled_by_user")
        else:
            next_time = self.now() + delta
            next_date = datetime.fromtimestamp(next_time).strftime('%Y-%m-%d %H:%M:%S')
            results['info'] = 'next run at ' + next_date
            self.post_job(skey, next_time)

        ntracks = len(results['tids']) if 'tids' in results else 0
        results['oinfo'] = 'generated ' + str(ntracks) + ' tracks'
        rkey = mk_sched_key('results', user, pid)
        jresults = json.dumps(results, indent=2)
        # print jresults
        self.r.lpush(rkey, jresults)
        self.r.ltrim(rkey, 0, self.max_retained_results - 1)
        self.r.expire(rkey, self.max_age_results)
        show_results(results)


    def now(self):
        return int(time.time())

    def process_job_queue(self):
        print 'starting job pusher'
        while True:
            skey = self.wait_for_next()
            if skey:
                print '    pushing', skey
                self.r.rpush(self.proc_queue, skey)

    def process_jobs(self):
        print 'starting job processor'
        while True:
            _,skey = self.r.blpop(self.proc_queue)
            if skey:
                print '   processing', skey
                self.run_job(skey)
            else:
                break
        print 'shutting down job processor'

    def start_processing_threads(self, threads=5):
        def worker():
            self.process_jobs()

        self.show_info()

        for i in xrange(threads):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
        sched.process_job_queue()

    def show_info(self):
        count = self.r.zcount(self.job_queue, -sys.maxint, sys.maxint)
        print 'job queue has', count, 'jobs'

        
def show_results(result):
    try:
        print "%s %s %.2f" % (result['status'], fmt_date(result['runtime']), result['time'])
        print result['oinfo']
        print result['info']
        if result['status'] == 'ok':
            print result['name']
            print result['uri']
        else:
            print result['message']
        print
    except:
        raise
        print "trouble showing formatted result"
        print json.dumps(result, indent=2)
        print

def fmt_date(ts):
    the_date = date.fromtimestamp(ts)
    return the_date.strftime("%Y-%m-%d")
        
        
def mk_sched_key(op, user, pid):
    return 'sched-' + op + '-' + user + '-' + pid

if __name__ == '__main__':
    import random
    import spotify_auth

    my_redis = redis.StrictRedis(host='redis1', port=6379, db=0)
    my_auth = spotify_auth.SpotifyAuth(r=my_redis)
    my_pm = program_manager.ProgramManager(my_auth, r=my_redis)

    sched = Scheduler(my_redis, my_pm)

    threads = 5
    if len(sys.argv) > 1:
        threads = int(sys.argv[1])

    sched.start_processing_threads(threads)
