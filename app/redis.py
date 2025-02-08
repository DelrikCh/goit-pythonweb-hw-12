from dotenv import load_dotenv
from enum import Enum
import os
import redis

load_dotenv()


class RedisDB:
    class DBs(Enum):
        PENDING_USERS = 0
        CURRENT_ACTIVE_USERS = 1
        PENDING_PASSWORD_RESETS = 2

    _instance = None
    _clients = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            for db in RedisDB.DBs:
                cls._instance._clients[db] = redis.Redis(
                    host=os.getenv("REDIS_HOST"),
                    port=os.getenv("REDIS_PORT"),
                    db=db.value,
                    decode_responses=True,
                )
        return cls._instance

    @classmethod
    def select(cls, db: DBs) -> redis.Redis:
        return cls._instance._clients[db]
