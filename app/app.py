from flask import Flask, request, jsonify, make_response, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select, create_engine
import os
import babel
from babel.dates import format_datetime
from datetime import datetime
import json
import sys

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')

db = SQLAlchemy()

engine = create_engine(os.getenv('DB_URL'))

def create_app():
    app = Flask(__name__)

    return app

app = create_app()

class Event(db.Model):
    __tablename__ = 'baby_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_ts = db.Column(db.DateTime(timezone=True), default=datetime.now)
    event_date = db.Column(db.Date, default=func.current_date)
    event_time = db.Column(db.Time(timezone=True), default=func.now())
    event_type = db.Column(db.String(80), nullable=False)
    event_duration = db.Column(db.Integer) # duration in minutes

    def json(self):
        return {'id': self.id,
                'event_ts': self.event_ts, 
                'event_date': self.event_date,
                'event_time' : self.event_time,
                'event_type': self.event_type, 
                'event_duration': self.event_duration}


with app.app_context():
        db_url = os.getenv('DB_URL')
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url 
        db.init_app(app)
        db.create_all()

def get_day_counts(for_date=None):

    filter_date = for_date
    if filter_date == None:
      filter_date = datetime.today().strftime("%Y-%m-%d")

    # print("get_day_counts: filter_date = " + filter_date, file=sys.stderr)
    with engine.connect() as conn:
      result = conn.execute(
            select(Event.event_type, func.count(Event.id).label('count'))
            .filter(Event.event_date == filter_date)
            .group_by(Event.event_type)
      )
    
    counts_dict = {}
    for item in result.all():
      counts_dict[item[0]] = item[1]
    
    # print("get_day_counts: Counts => " + str(counts_dict), file=sys.stderr)
    return counts_dict

def get_day_wise_counts():

    with engine.connect() as conn:
        result = conn.execute(
                select(Event.event_date, Event.event_type, func.count(Event.id).label('count'))
                .group_by(Event.event_date, Event.event_type)
                .order_by(Event.event_date.desc(), Event.event_type)
        )
    
       # print(result.all())

        day_wise_counts_data = []
        for row in result.all():
            day_counts_dict={}
            row_dict = row._asdict()  
           #  print(row_dict)      
            day_counts_dict['event_date'] = row_dict['event_date'].strftime("%Y-%m-%d")
            day_counts_dict['event_type'] = row_dict['event_type']
            day_counts_dict['count'] = row_dict['count']
            day_wise_counts_data.append(day_counts_dict)
            
        day_wise_counts_data_json = json.dumps(day_wise_counts_data, indent=4)
    
        day_wise_counts_data_string = json.loads(day_wise_counts_data_json)

    return day_wise_counts_data_string

@app.context_processor
def inject_now():
   return { 'now': datetime.now() }

@app.template_filter()
def format_datetime(value, format='medium'):
    if format == 'full':
        format="EEEE, d. MMMM y 'at' HH:mm"
    elif format == 'medium':
        format="EE dd.MM.y HH:mm"
    elif format == 'compact':
       format='EEE MM/dd/y hh:mm a'
    return babel.dates.format_datetime(value, format)

# create a test route
@app.route("/", methods=['GET','POST'])
def index():

    if request.method == 'GET':
        day_counts = get_day_counts()
        day_wise_counts = get_day_wise_counts()
        return render_template("index.html", 
                               title="Baby Tracking", 
                               day_counts=day_counts,
                               day_wise_counts=day_wise_counts)
    else:
        event_type = None
        duration = 0
        if request.form.get('feeding') == "Feeding":
           event_type = "Feeding"
           duration = request.form.get('duration-time')
        elif request.form.get('wet') == "Wet":
           event_type = "Wet Diaper"
        elif request.form.get('dirty') == "Dirty":
           event_type = "Dirty Diaper"

        event_date = datetime.today().strftime("%Y-%m-%d")
        try:
           event_date = request.form.get('event-date')
           print("form date = ", event_date)
        except Exception as e:
           event_date = datetime.today().strftime("%Y-%m-%d")

        event_time = datetime.now().strftime("%H:%M:%S.%f%z")
        try:
           event_time_str = request.form.get('event-time')
           event_time_obj = datetime.strptime(event_time_str, "%H:%M %p")
           print(event_time_obj)
           event_time = event_time_obj.strftime("%H:%M:%S.%f%z")
           print("event time", event_time)
        except Exception as e:
           event_time = datetime.now().strftime("%H:%M:%S.%f%z")
           print("Exception event time", event_time)

        new_event = Event(event_type=event_type, 
                          event_date=event_date, 
                          event_time=event_time,
                          event_duration=duration)
        db.session.add(new_event)
        db.session.commit()

        day_counts = get_day_counts()
        day_wise_counts = get_day_wise_counts()

        return render_template("index.html", 
                               title="Baby Tracking", 
                               day_counts=day_counts,
                               day_wise_counts=day_wise_counts)

@app.route('/test', methods=['GET'])
def test():
  return make_response(jsonify({'message': 'test route'}), 200)

# create an event
@app.route('/events', methods=['POST'])
def create_event():
  try:
    data = request.get_json()
    new_event = Event(event_type=data['event_type'])
    db.session.add(new_event)
    db.session.commit()
    return make_response(jsonify({'message': 'event created'}), 201)
  except Exception as e:
    return make_response(jsonify({'message': 'error creating event'}), 500)

# get all events
@app.route('/events', methods=['GET'])
def get_events():
  try:

    with engine.connect() as conn:
      result = conn.execute(
            select(Event.id, 
                   Event.event_date,
                   Event.event_time,
                   Event.event_type, 
                   Event.event_duration)
            .order_by(Event.event_date, Event.event_time)
      )

    events_data = []
    for row in result.all():
       event_dict={}
       row_dict = row._asdict()
       event_dict['id'] = row_dict['id']
       event_dict['event_date'] = row_dict['event_date'].strftime("%Y-%m-%d")
       event_dict['event_time'] = row_dict['event_time'].strftime("%H:%M:%S")
       event_dict['event_type'] = row_dict['event_type']
       event_dict['event_duration'] = row_dict['event_duration']
       events_data.append(event_dict)
    
    events_json = json.dumps(events_data, indent=4)
    print(events_json)
  
    events_json_string = json.loads(events_json)

    return render_template("events.html", title="Baby Tracking - Events", events=events_json_string)
  
  except Exception as e:
    print(f"Exception {e} -> {type(e)}")
    return make_response(jsonify({'message': 'error getting events'}), 500)

# get a user by id
@app.route('/events/<int:id>', methods=['GET'])
def get_event(id):
  try:
    event = Event.query.filter_by(id=id).first()
    if event:
      return make_response(jsonify({'event': event.json()}), 200)
    return make_response(jsonify({'message': 'event not found'}), 404)
  except Exception as e:
    return make_response(jsonify({'message': 'error getting event'}), 500)

# update a user
@app.route('/events/<int:id>', methods=['PUT'])
def update_event(id):
  try:
    event = Event.query.filter_by(id=id).first()
    if event:
      data = request.get_json()
      event.event_type = data['event_type']
      db.session.commit()
      return make_response(jsonify({'message': 'event updated'}), 200)
    return make_response(jsonify({'message': 'event not found'}), 404)
  except Exception as e:
    return make_response(jsonify({'message': 'error updating event'}), 500)

# delete a event
@app.route('/events/<int:id>', methods=['DELETE'])
def delete_event(id):
  try:
    event = Event.query.filter_by(id=id).first()
    if event:
      db.session.delete(event)
      db.session.commit()
      return make_response(jsonify({'message': 'event deleted'}), 200)
    return make_response(jsonify({'message': 'event not found'}), 404)
  except Exception as e:
    return make_response(jsonify({'message': 'error deleting event'}), 500)
  

  if __name__ == '__main__':
    app.run()