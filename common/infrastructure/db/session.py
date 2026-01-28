"""
Archivo que contiene la clase Database y la función get_db.
"""

import os
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.session import close_all_sessions


engines = {}


class RoutingSession(Session):
    """
    Clase de sesión personalizada que permite el enrutamiento dinámico de conexiones a la base de datos.

    Esta clase hereda de la clase Session de SQLAlchemy y proporciona funcionalidad para enrutamiento dinámico
    de conexiones a motores de bases de datos. Esto se logra utilizando el atributo "_name", que puede ser None
    o un nombre de motor de base de datos específico.
    """

    # Atributo de clase que puede ser None o un nombre de motor de base de datos específico.
    _name = None

    def get_bind(self, mapper: Any | None = None, clause: Any | None = None) -> Any:
        """
        Sobrescribe el método get_bind de la clase Session de SQLAlchemy para obtener el motor de base de datos
        adecuado en función del contexto.

        :param mapper: El objeto de asignación de SQLAlchemy.
        :type mapper: Mapper or None
        :param clause: Una cláusula de SQL.
        :type clause: ClauseElement or None
        :return: El motor de base de datos correspondiente al contexto.
        :rtype: Engine
        """
        if self._name:  # pylint: disable=R1705
            return engines[self._name]
        elif mapper:
            return engines["reader"]
        elif self._flushing:
            return engines["writer"]

    def using_bind(self, name: str) -> "RoutingSession":
        """
        Crea una nueva instancia de RoutingSession con un motor de base de datos específico.

        :param name: El nombre del motor de base de datos.
        :type name: str
        :return: Una nueva instancia de RoutingSession con el motor de base de datos especificado.
        :rtype: RoutingSession
        """
        s = RoutingSession()
        vars(s).update(vars(self))
        s._name = name  # pylint: disable=W0212
        return s


class Database:
    """
    Clase que maneja la configuración y creación de conexiones a la base de datos.

    Esta clase se encarga de configurar y establecer conexiones a la base de datos, ya sea una base de datos SQLite
    local o una base de datos PostgreSQL remota. También gestiona la creación de sesiones de base de datos para
    operaciones de lectura y escritura.
    """

    def __init__(self) -> None:
        global engines  # pylint: disable=W0602
        if os.environ["DATABASE_CONNECTION"] == "mysql":
            self.SQLALCHEMY_DATABASE_URL_WRITER = (
                "mysql+mysqlconnector://{}:{}@{}:{}/{}".format(
                    os.getenv("DB_USER"),
                    os.getenv("DB_PASSWORD"),
                    os.getenv("DB_HOST_WRITER"),
                    os.getenv("DB_PORT"),
                    os.getenv("DB_NAME"),
                )
            )
            self.SQLALCHEMY_DATABASE_URL_READ = (
                "mysql+mysqlconnector://{}:{}@{}:{}/{}".format(
                    os.getenv("DB_USER"),
                    os.getenv("DB_PASSWORD"),
                    os.getenv("DB_HOST_READ"),
                    os.getenv("DB_PORT"),
                    os.getenv("DB_NAME"),
                )
            )
        elif os.environ["DATABASE_CONNECTION"] == "postgres":
            self.SQLALCHEMY_DATABASE_URL_WRITER = "postgresql://{}:{}@{}:{}/{}".format(
                os.getenv("DB_USER"),
                os.getenv("DB_PASSWORD"),
                os.getenv("DB_HOST_WRITER"),
                os.getenv("DB_PORT"),
                os.getenv("DB_NAME"),
            )
            self.SQLALCHEMY_DATABASE_URL_READ = "postgresql://{}:{}@{}:{}/{}".format(
                os.getenv("DB_USER"),
                os.getenv("DB_PASSWORD"),
                os.getenv("DB_HOST_READ"),
                os.getenv("DB_PORT"),
                os.getenv("DB_NAME"),
            )
        engines["writer"] = create_engine(
            self.SQLALCHEMY_DATABASE_URL_WRITER, logging_name="writer", echo=False
        )
        engines["reader"] = create_engine(
            self.SQLALCHEMY_DATABASE_URL_READ, logging_name="reader", echo=False
        )
        self.Session = sessionmaker(
            autocommit=False, autoflush=False, class_=RoutingSession
        )


def close_engines() -> None:
    """
    Cierra todas las conexiones a las bases de datos.

    Esta función cierra todas las conexiones de motores de bases de datos almacenados en la variable global "engines".
    """
    for engine in engines.values():
        engine.dispose()


def get_db() -> Generator[Session, None, None]:
    """
    Obtiene una sesión de base de datos para realizar operaciones.

    :return: Una sesión de base de datos.
    :rtype: Session
    """
    db = Database()
    try:
        yield db.Session()
    finally:
        close_all_sessions()
