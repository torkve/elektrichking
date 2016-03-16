from datetime import datetime, timezone, timedelta
from configparser import ConfigParser
from urllib.request import urlopen
from json import loads
from itertools import product, groupby, chain
from flask import Flask, render_template
import sys
import traceback

cfg = ConfigParser()
cfg.read('rasp.ini')
api_key = cfg['global']['api_key']
url = 'https://api.rasp.yandex.net/v1.0/search/?apikey={api_key}&format=json&from={fr}&to={to}&lang=ru&date={date}&page={page}'

app = Flask(__name__)

tz = timezone(timedelta(0, 60*60*3), 'MSK')

gn = {
    "name": "ГН",
    "name_gen": "в ГН",
    "loc": (55.957869, 37.446412),
    "station_ids": ["s9837361"],
}

locations = {
    "msk": {
        "name": "Москва",
        "name_gen": "в Москве",
        "loc": (55.776276, 37.654846),
        "station_ids": ["s2006004"],
        "int": {
            "name": "Химки",
            "name_gen": "в Химках",
            "loc": (55.894402, 37.451995),
            "station_ids": ["s9603401", "s9743047"],
        },
    },
    "pr": {
        "name": "ПР",
        "name_gen": "на ПР",
        "loc": (55.837404, 37.571898),
        "station_ids": ["s9603458"],
        "int": {
            "name": "Химки",
            "name_gen": "в Химках",
            "loc": (55.894402, 37.451995),
            "station_ids": ["s9603401", "s9743047"],
        },
    },
    "rizh": {
        "name": "Рижская",
        "name_gen": "на Рижской",
        "loc": (55.794065, 37.637583),
        "station_ids": ["s9603518"],
        "int": {
            "name": "Химки",
            "name_gen": "в Химках",
            "loc": (55.894402, 37.451995),
            "station_ids": ["s9603401", "s9743047"],
        },
    },
    "mega": {
        "name": "Мега",
        "name_gen": "в Ашане",
        "loc": (55.911297, 37.404624),
        "station_ids": ["s9743030"],
        "int": None,
    },
}

last_update_times = {}

rasps = {}
connections = {}


def n(f, t, i=None):
    if i:
        return "{}_2_{}_{}".format(f, t, i)
    return "{}_2_{}".format(f, t)


def download(date, fr, to, page=1):
    u = url.format(api_key=api_key, fr=fr, to=to, date=date, page=page)
    print("loading {}".format(u))
    req = loads(str(urlopen(u).read(), 'utf-8'))
    print("loaded")
    
    data = req['threads']
    if req['pagination']['has_next']:
        data += download(date, fr, to, page=page + 1)
    return data


def update_rasp(name, loc_from, loc_to, now):
    if (name in last_update_times
        and (now - last_update_times[name]).seconds < 60 * 60 * 2
        and now.day == last_update_times[name].day
    ):
        return

    last_update_times[name] = now
    date = now.strftime('%Y-%m-%d')

    rasps[name] = []
    print("updating {}".format(name))
    for from_id in loc_from["station_ids"]:
        for to_id in loc_to["station_ids"]:
            rasps[name] += download(date, from_id, to_id)


def update_rasps(direction):
    now = datetime.now(tz=tz)

    info = locations[direction]
    
    if info["int"] is not None:
        update_rasp(n("gn", "int"), gn, info["int"], now)
        update_rasp(n("int", direction), info["int"], info, now)
        update_rasp(n("int", "gn"), info["int"], gn, now)
        update_rasp(n(direction, "int"), info, info["int"], now)

        connections[n("gn", direction)] = [pair
                                           for pair in product(
                                               rasps[n("gn", "int")],
                                               rasps[n("int", direction)])
                                           if pair[0]['arrival'] < pair[1]['departure']]
        connections[n(direction, "gn")] = [pair
                                           for pair in product(
                                               rasps[n(direction, "int")],
                                               rasps[n("int", "gn")])
                                           if pair[0]['arrival'] < pair[1]['departure']]
    else:
        update_rasp(n("gn", direction), gn, info, now)
        update_rasp(n(direction, "gn"), info, gn, now)


def render_rasp(direction):
    now = datetime.now(tz=tz)

    cons = {}
    routes = {}

    if locations[direction]["int"] is not None:
        routes["gn2int"] = get_routes('gn', 'int', now)
        routes["int2gn"] = get_routes('int', 'gn', now)
        routes["dest2int"] = get_routes(direction, 'int', now)
        routes["int2dest"] = get_routes('int', direction, now)

        cons["gn2dest"] = get_connections('gn', direction, now)[:8]
        for r in cons["gn2dest"]:
            r['dur'] = format_duration(r['dur'])
        cons["dest2gn"] = get_connections(direction, 'gn', now)[:8]
        for r in cons["dest2gn"]:
            r['dur'] = format_duration(r['dur'])
    else:
        routes["gn2dest"] = get_routes('gn', direction, now)
        routes["dest2gn"] = get_routes(direction, 'gn', now)

    return render_template('rasp.html',
                           gn=gn,
                           direction=direction,
                           locations=locations,
                           connections=cons,
                           routes=routes,
    )


def format_duration(dur):
    secs = int(dur % 60)
    mins = int(dur / 60)

    hours = int(mins / 60)
    mins = int(mins % 60)

    res = []
    if hours > 0:
        res.append('{} ч'.format(hours))
    if mins > 0:
        res.append('{} мин'.format(mins))
    if secs > 0:
        res.append('{} с'.format(secs))
    return ' '.join(res)


def get_connections(name_from, name_to, now):
    res = []
    for row in connections[n(name_from, name_to)]:
        dep = datetime.strptime(row[0]['departure'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz)

        if dep < now:
            continue

        arr_int = datetime.strptime(row[0]['arrival'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz)
        dep_int = datetime.strptime(row[1]['departure'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz)
        arr = datetime.strptime(row[1]['arrival'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz)
        num1 = row[0]['thread']['number']
        num2 = row[1]['thread']['number']
        
        dur = (arr - dep).seconds
        res.append(dict(dur=dur,
                   dep=dep.strftime('%H:%M'),
                   arr_int=arr_int.strftime('%H:%M'),
                   dep_int=dep_int.strftime('%H:%M'),
                   arr=arr.strftime('%H:%M'),
                   num1=num1,
                   num2=num2,
                   typeimg1="https://yandex.st/rasp/3.25e4a6a/blocks-desktop/b-transico/b-transico__bus.png" if row[0]["thread"]["transport_type"] == "bus" else "https://yandex.st/rasp/3.25e4a6a/blocks-desktop/b-transico/b-transico__suburban.png",
                   typeimg2="https://yandex.st/rasp/3.25e4a6a/blocks-desktop/b-transico/b-transico__bus.png" if row[1]["thread"]["transport_type"] == "bus" else "https://yandex.st/rasp/3.25e4a6a/blocks-desktop/b-transico/b-transico__suburban.png",
                  ))
    return sorted(
        (sorted(r, key=lambda x: x['dur'])[0]
         for k, r in groupby(sorted(res, key=lambda x: (x['num1'], x['dep'])), lambda x: (x['num1'], x['dep']))),
        key=lambda x: (x['dep'], x['dur'])
    )


def get_routes(name_from, name_to, now):
    for row in rasps[n(name_from, name_to)]:
        dep = datetime.strptime(row['departure'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz)
        if dep < now:
            continue
        yield dict(num=row['thread']['number'],
                   departure=dep.strftime('%H:%M'),
                   title=row['thread']['short_title'].split(' - ')[-1],
                   arrival=datetime.strptime(row['arrival'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
                  )
    

@app.route('/rasp/')
@app.route('/rasp/<direction>')
def application(direction="msk"):
    update_rasps(direction)
    # start_response('200 OK', [('Content-Type', 'text/html')])
    # return [bytes(render_rasp(), "utf-8")]
    try:
        return bytes(render_rasp(direction), "utf-8")
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        raise


# vim: set ts=4 sts=4 sw=4 et :
