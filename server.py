from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask
app = Flask(__name__) 

from db_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/hello')
def here():
    restaurant = session.query(Restaurant).first()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    output = ''
    for item in items:
        output += item.name
        output += '<br />'
    return output


if __name__ == "__main__":
    app.debug = True
    app.run(host='127.0.0.1', port=5000)