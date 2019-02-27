import sys

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Restaurant(Base):
    __tablename__ = 'restaurant'
    name = Column(
        String(80), nullable = False
    )
    id = Column(
        Integer, primary_key = True
    )
    @property
    def serialize(self):
        # Return object data in easily serialisable format
        return {
            'name': self.name,
            'id': self.id
        }


class MenuItem(Base):
    __tablename__ = 'menu_item'
    name = Column(
        String(80), nullable = False
    )
    id = Column(
        Integer, primary_key = True
    )
    course = Column(String(250))
    description = Column(String(250))
    price = Column(String(8))
    restaurant_id = Column(
        Integer, ForeignKey('restaurant.id')
    )
    restaurant = relationship(Restaurant)

    @property
    def serialize(self):
        # Return object data in easily serialisable format
        return {
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'restaurant_id': self.restaurant_id,
            'course': self.course,
        }

class User(Base):
    __tablename__ = 'user'
    name = Column(
        String(80), nullable = False
    )
    email = Column(
        String(80), nullable = False
    )
    picture = Column(
        String(160), nullable = False
    )
    id = Column(
        Integer, primary_key = True
    )

    @property
    def serialize(self):
        # Return object data in easily serialisable format
        return {
            'name': self.name,
            'email': self.email,
            'picture': self.picture,
            'id': self.id
        }

def main():
    pass


if __name__ == "__main__":
    main()


engine = create_engine(
    'sqlite:///restaurantmenu.db'
)

Base.metadata.create_all(engine)

