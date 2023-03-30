'''
  program manager

'''

import redis
import simplejson as json
import hashlib
import random
import time
import pbl
import compiler
import plugs
import traceback
import kvstore

debug_exceptions = False


'''
    schema:

        programs:

            program:pid json-string

        directory
            directory:user list-of-pids


'''

class ProgramManager:

    def __init__(self, auth, r = None):
        self.use_file_store_for_programs = True
        self.auth = auth
        if r:
            self.r = r
        else:
            self.r = redis.StrictRedis(host='localhost', port=6379, db=0)

        ''' program looks like

            {
                name: '',
                main:'',
                description:"",
                pid:'',
                components : [],
                extra : {},
                owner: 'plamere',
                uri:  'spotify:plamere:12345678'
                schedule: {
                    enabled: true,
                    start
                },
            }
        '''
        if debug_exceptions:
            print "WARNING: debugging exceptions"


    def add_program(self, user, program):
        ''' add the program to the db

            get an id for the program
            save the program to redis
            add the program to the dirctory
            return the id
        '''

        pid = make_pid(program)
        program['pid'] = pid
        program['uri']  = None

        self.save_program(user, program)

        dirkey = mkkey('directory', user)
        self.r.rpush(dirkey, pid)
        self.add_stat(pid, 'creation_date', int(time.time()))
        self.add_info(pid, 'shared', "False")
        self.add_info(pid, 'owner', user)
        self.add_info(pid, 'name', program['name'])
        self.add_info(pid, 'description', program['description'])

        return pid

    def save_program(self, user, program):
        if self.use_file_store_for_programs:
            self.save_program_to_disk(user, program)
        else:
            pid = program['pid']
            pkey = mkprogkey(user, pid)
            self.r.set(pkey, json.dumps(program))

    def get_program(self, user, pid):
        if self.use_file_store_for_programs:
            program = self.load_program_from_disk(user, pid)
        else:
            pkey = mkprogkey(user, pid)
            val = self.r.get(pkey)
            if val:
                program = json.loads(val)
            else:
                program = None
        return program


    def save_program_to_disk(self, user, program):
        pid = program['pid']
        fkey = mkfilekey(user, pid)
        kvstore.put(fkey, json.dumps(program))

    def load_program_from_disk(self, user, pid):
        fkey = mkfilekey(user, pid)
        prog_js = kvstore.get(fkey)
        if prog_js:
            program = json.loads(prog_js)
        else:
            program = None
        return program

    def directory(self, user, start, count):
        dirkey = mkkey('directory', user)
        pids = self.r.lrange(dirkey, start, count - 1)

        programs = [self.get_program(user, pid) for pid in pids]

        out = []
        total  = self.r.llen(dirkey)
        for program, pid in zip(programs, pids):
            if program:
                if 'description' in program:
                    desc = program['description']
                else:
                    desc = ""
                info = {
                    'name': program['name'],
                    'description': desc,
                    'pid': pid,
                    'ncomponents': len(program['components']),
                    'shared' : False
                }
                info.update(program['extra'])
                info.update(self.get_stats(pid))
                info.update(self.get_info(pid))
                info['shared'] = info['shared'] == 'True'
                if "owner" not in info:
                    info["owner"] = user
                    print "directory:patched owner", user
                out.append(info)
        out.sort(key=lambda x:x['name'].lower())
        return total, out

    def copy_program(self, user, pid):
        program = self.get_program(user, pid)
        if program:
            program['name'] = 'copy of ' + program['name']
            pid = self.add_program(user, program)
        return program

    def import_program(self, user, pid):
        new_pid = None
        info = self.get_info(pid)
        if info and 'shared' in info:
            is_shared =  info['shared'] == 'True'
            if is_shared:
                owner =  info['owner']
                program = self.get_program(owner, pid)
                program['name'] = 'import of ' + program['name']
                new_pid = self.add_program(user, program)
                self.incr_import(pid)
        self.inc_global_counter("program_imports")
        return new_pid

    def publish_program(self, user, pid, state):
        self.add_info(pid, 'shared', state)
        if state:
            self.r.sadd('published-programs', pid)
            self.inc_global_counter("program_published")
        else:
            self.r.srem('published-programs', pid)

    def get_published_programs(self):
        return self.r.smembers('published-programs')


    def delete_program(self, user, pid):
        dirkey = mkkey('directory', user)
        removed_count = self.r.lrem(dirkey, 1, pid)
        if removed_count >= 1:
            if self.use_file_store_for_programs:
                fkey = mkfilekey(user, pid)
                kvstore.delete(fkey)
            else:
                pkey = mkprogkey(user, pid)
                self.r.delete(pkey)
            self.del_info(pid)
            self.inc_global_counter("program_deletes")
        return removed_count >= 1

    def update_program(self, user, program):
        self.save_program(user, program)
        pid = program['pid']
        dirkey = mkkey('directory', user)
        self.r.lrem(dirkey, 1, pid)
        self.r.rpush(dirkey, pid)
        self.add_info(pid, 'owner', user)
        self.add_info(pid, 'name', program['name'])
        self.add_info(pid, 'description', program['description'])
        self.inc_global_counter("program_updates")

    def add_stat(self, pid, key, val):
        pkey = mkkey('program-stats', pid)
        self.r.hset(pkey, key, val)

    def inc_stat(self, pid, key):
        pkey = mkkey('program-stats', pid)
        self.r.hincrby(pkey, key, 1)

    def get_stats(self, pid):
        pkey = mkkey('program-stats', pid)
        stats = self.r.hgetall(pkey)
        out = {}
        for k, v in stats.items():
            out[k] = int(float(v))
        return out

    def add_info(self, pid, key, val):
        pkey = mkkey('program-info', pid)
        self.r.hset(pkey, key, val)

    def get_info(self, pid, key = None):
        pkey = mkkey('program-info', pid)
        if key == None:
            return self.r.hgetall(pkey)
        else:
            return self.r.hget(pkey, key)

    def del_info(self, pid):
        pkey = mkkey('program-info', pid)
        self.r.delete(pkey)

    def incr_import(self, pid):
        pkey = mkkey('program-info', pid)
        self.r.hincrby(pkey, 'imports', 1)


    def execute_program(self, auth_code, pid, save_playlist):
        start = time.time()

        results = { }

        self.inc_global_counter("programs_executed")
        try:
            pbl.engine.clearEnvData()
            token = self.auth.get_fresh_token(auth_code)
            if not token:
                print 'WARNING: bad auth token', auth_code
                results['status'] = 'error'
                results['message'] = 'not authorized'
            else:
                delta = token['expires_at'] - time.time()
                print 'cur token expires in', delta, 'secs'
                user = token['user_id']
                program = self.get_program(user, pid)
                if not program:
                    return None
                pbl.engine.setEnv('spotify_auth_token', token['access_token'])
                pbl.engine.setEnv('spotify_user_id', token['user_id'])

                print 'executing', user, pid
                # print '# executing', json.dumps(program, indent=4)
                status, obj = compiler.compile(program)
                print 'compiled in', time.time() - start, 'secs'

                if 'max_tracks' in program:
                    max_tracks = program['max_tracks']
                else:
                    max_tracks = 40

                results['status'] = status

                if status == 'ok':
                    results['name'] = obj.name
                    tids = pbl.get_tracks(obj, max_tracks)
                    results['tids'] = tids
                    self.inc_global_counter("tracks_generated", len(tids))

                    if save_playlist:
                        uri = self.get_info(pid, 'uri')
                        self.inc_global_counter("playlists_updated")
                        new_uri = plugs.save_to_playlist(program['name'], uri, tids)
                        if uri != new_uri:
                            self.add_info(pid, 'uri', new_uri)
                        if new_uri:
                            results['uri'] = new_uri
                        else:
                            results['status'] = 'error'
                            results['message'] = "Can't save playlist to Spotify"
                else:
                    self.inc_global_counter("programs_execute_errors")
                    results['status'] = 'error'
                    results['message'] = status

        except pbl.PBLException as e:
            results['status'] = 'error'
            results['message'] = e.reason
            if e.component and e.component.name in program['hsymbols']:
                cname = program['hsymbols'][e.component.name]
            else:
                cname = e.cname
            results['component'] = cname
            print 'PBLException', json.dumps(results, indent=4)
            traceback.print_exc()
            if debug_exceptions:
                raise

        except Exception as e:
            results['status'] = 'error'
            results['message'] = str(e)
            print 'General Exception', json.dumps(results, indent=4)
            traceback.print_exc()
            if debug_exceptions:
                raise

        pbl.engine.clearEnvData()
        results['time'] = time.time() - start
        print 'compiled and executed in', time.time() - start, 'secs'

        self.add_stat(pid, 'last_run', time.time());
        if results['status'] == 'ok':
            self.inc_stat(pid, 'runs');
        else:
            self.inc_stat(pid, 'errors');

        print 'run', time.time() - start, results['status']
        return results

    def share_program(self, user, pid):
        pass

    def unshare_program(self, user, share_id):
        pass

    def schedule_program(self, token, user, pid):
        pass

    def inc_global_counter(self, name, count=1):
        self.r.hincrby("global_stats", name, count)

    def get_global_stats(self):
        return self.r.hgetall("global_stats")


def mkkey(type, id):
    return type + ':' + id

def mkprogkey(user, id):
    return 'program:' + user + ':' + id

def mkfilekey(user, id):
    return id.encode("UTF-8") + "." + user

def make_pid(program):
    salt = random.randint(0, 1000000)
    js = json.dumps(program) + str(salt)
    md5 = hashlib.md5(js).hexdigest()
    return md5


if __name__ == '__main__':
    import sys
    import pprint

    p = ProgramManager()
    user = sys.argv[1]

    def mk_program():
        return {
            "name": 'tst',
            "main":'main',
            "components" : [],
            "extra" : {},
            "schedule": {
            }
        }

    def show_dir(user):
        for pid in p.directory(user):
            print pid,
            program = p.get_program(user, pid)
            pprint.pprint(program)
            print



    print 'dir', p.directory(user)

    program = mk_program()
    p.add_program(user, program)
    show_dir(user)
