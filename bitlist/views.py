from bitlist.db.cache import Cache
from bitlist.models.user import User
from bitlist.models.song import Song
from helpers import add_to_playlist
from helpers import current_playlist
from helpers import get_random_song
from helpers import redis_song_library
from helpers import get_song_by_id
import jobs
import json
import player
from pyramid.security import remember
from pyramid.security import forget
from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPFound
from .models.song import Song


# =====     Authentication Routes ======
@view_config(route_name='login', renderer='templates/login.jinja2')
@forbidden_view_config(renderer='templates/login.jinja2')
def login(request):
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/player' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        if User.check_password(login, password):
            headers = remember(request, login)
            return HTTPFound(location = came_from,
                             headers = headers)
        message = 'Failed login'
    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password,
    )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = "{}/login".format(request.application_url),
                     headers = headers)

# ======    FRONT END ROUTES   ==========
@view_config(route_name='player', renderer='templates/player.jinja2',
             permission='listen')
def player_view(request):
    server_path = "http://{}:8000".format(request.host.split(':')[0])
    status = request.mpd.status()
    playlist = current_playlist()
    #if status['state'] != 'play':
    #    random_song = get_random_song()
    #    add_to_playlist(request, random_song.id)
    #    request.mpd.play()
    #    status['state'] = 'play'
    return { 'playlist': playlist,
             'status': status,
             'player_host': server_path,
             'library': redis_song_library()}


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'project': 'bitlist'}

@view_config(route_name='songs', renderer='json')
def library(request):
    available_music = redis_song_library()
    return dict(songs=available_music)

@view_config(route_name='songinfo', renderer='json')
def library(request):
    song = Song.get_by_id(request.matchdict['songid']) 
    return song

# =======   MUSIC DAEMON CONTROLS =======
@view_config(route_name='play', renderer='json')
def player_play(request):
    request.mpd.play()
    return {'Status': 'Success'}

@view_config(route_name='skip', renderer='json')
def player_skip(request):
    request.mpd.next()

@view_config(route_name='status', renderer='json')
def player_status(request):
    return request.mpd.status()

@view_config(route_name='playlist', renderer='json')
def player_playlist(request):
    return current_playlist()

@view_config(route_name='playlistshuffle', renderer='json')
def player_playlist_shuffle(request):
    request.mpd.shuffle()
    return request.mpd.playlist()

@view_config(route_name='playlistseed', renderer='json')
def player_playlist_seed(request):
    pid = jobs.warm_db_cache.delay()
    return {'JobID': pid.id}


@view_config(route_name='playlistclear', renderer='json')
def player_playlist_clear(request):
    request.mpd.clear()
    return request.mpd.playlist()

@view_config(route_name='playlistenqueue', renderer='json')
def player_playlist_enqueue(request):
    add_to_playlist(request, request.matchdict['song'])
    return current_playlist()


# ======== FETCH API CONTROLS =======

@view_config(route_name='fetch_youtube', renderer='json')
def fetch_youtube_url(request):
    pid = jobs.transcode_youtube_link.delay(request.matchdict['videoid'])
    return {'JobID': pid.id}

@view_config(route_name='fetch_soundcloud', renderer='json')
def fetch_soundcloud_url(request):
    pid = jobs.transcode_soundcloud_link.delay(request.matchdict['user'],
                                               request.matchdict['songid'])
    return {'JobID': pid.id}

@view_config(route_name='fetch_spotify', renderer='json')
def fetch_spotify_url(request):
    pid = jobs.transcode_spotify_link.delay(request.matchdict['resource'])
    return {'JobID': pid.id}



# ======== Redis API CONTROLS =======
@view_config(route_name='update_cache', renderer='json')
def enqueue_update_cache(request):
    jobs.enqueue_s3_scraper()
    return {'Status': 'Success'}

