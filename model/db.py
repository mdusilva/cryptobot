import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, DATE, INTEGER, REAL, TIMESTAMP, JSONB
from sqlalchemy.orm import sessionmaker

cbpro_metadata = sqlalchemy.MetaData(schema="cb_pro")
Base = declarative_base(metadata=cbpro_metadata)

class Pairs(Base):
    __tablename__ = 'pairs'

    id = sqlalchemy.Column(UUID(as_uuid=True), primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    symbol = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)

    transactions = sqlalchemy.orm.relationship("Transaction", back_populates="pair")

class Execution(Base):
    __tablename__ = 'execution'

    id = sqlalchemy.Column(UUID(as_uuid=True), primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    parameters = sqlalchemy.Column(JSONB)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    
    positions = sqlalchemy.orm.relationship("Positions", back_populates="execution")
    portfolio_value = sqlalchemy.orm.relationship("PortfolioValue", back_populates="execution")
    transaction = sqlalchemy.orm.relationship("Transaction", back_populates="execution")

class Positions(Base):
    __tablename__ = 'positions'

    id = sqlalchemy.Column(UUID(as_uuid=True), primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    symbol = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    value = sqlalchemy.Column(REAL, nullable=False)
    timestamp = sqlalchemy.Column(TIMESTAMP)
    execution_id = sqlalchemy.Column(UUID(as_uuid=True), sqlalchemy.ForeignKey('execution.id'), nullable=False)

    execution = sqlalchemy.orm.relationship("Execution", back_populates="positions")

class PortfolioValue(Base):
    __tablename__ = 'portfolio_value'
    id = sqlalchemy.Column(UUID(as_uuid=True), primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    timestamp = sqlalchemy.Column(TIMESTAMP)
    value = sqlalchemy.Column(REAL)
    execution_id = sqlalchemy.Column(UUID(as_uuid=True), sqlalchemy.ForeignKey('execution.id'), nullable=False)

    execution = sqlalchemy.orm.relationship("Execution", back_populates="portfolio_value")

class Transaction(Base):
    __tablename__ = 'transaction'
    id = sqlalchemy.Column(UUID(as_uuid=True), primary_key=True, server_default=sqlalchemy.text("gen_random_uuid()"))

    timestamp = sqlalchemy.Column(TIMESTAMP)
    order_id = sqlalchemy.Column(sqlalchemy.String)
    pair_id = sqlalchemy.Column(UUID(as_uuid=True), sqlalchemy.ForeignKey('pairs.id'), nullable=False)
    size = sqlalchemy.Column(REAL)
    funds = sqlalchemy.Column(REAL)
    price = sqlalchemy.Column(REAL)
    side = sqlalchemy.Column(sqlalchemy.String)
    status = sqlalchemy.Column(sqlalchemy.String)
    execution_id = sqlalchemy.Column(UUID(as_uuid=True), sqlalchemy.ForeignKey('execution.id'), nullable=True)

    pair = sqlalchemy.orm.relationship("Pairs", back_populates="transactions")
    execution = sqlalchemy.orm.relationship("Execution", back_populates="transaction")

def connect_to_session():
    db_string = "postgresql://msilva:manuel123@localhost:5432/postgres"
    engine = sqlalchemy.create_engine(db_string, echo_pool=True, pool_recycle=3600, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

if __name__ == "__main__":
    session = connect_to_session()
    session.close()