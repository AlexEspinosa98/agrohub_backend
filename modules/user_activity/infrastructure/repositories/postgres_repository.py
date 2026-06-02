from datetime import date
from typing import List, Optional
import uuid
import hashlib

from database.mysql_connection import get_db_cursor
from modules.user_activity.domain.entities import (
    Association,
    AssociationUpdate,
    Logbook,
    LogbookUpdate,
    User,
    UserUpdate,
)

DEFAULT_ROLE = "user"


class UserActivityRepository:
    def __init__(self):
        self._create_tables()

    def _create_tables(self):
        with get_db_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS associations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    latitude DOUBLE,
                    longitude DOUBLE,
                    department VARCHAR(255),
                    municipality VARCHAR(255),
                    vereda VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL UNIQUE,
                    identification VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(255),
                    password_hash VARCHAR(255) NOT NULL,
                    association_id INT,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    auth_token VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_users_association FOREIGN KEY (association_id) REFERENCES associations(id)
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS logbooks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    association_id INT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    activity_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_logbooks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_logbooks_association FOREIGN KEY (association_id) REFERENCES associations(id)
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    user_id INT NOT NULL,
                    role ENUM('user', 'model') NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_conv_session (session_id),
                    CONSTRAINT fk_conv_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """
            )

    # Users
    def create_user(self, user: User) -> int:
        password_hash = hashlib.sha256(user.password.encode("utf-8")).hexdigest()
        role_value = user.role if getattr(user, "role", None) else DEFAULT_ROLE
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, phone, identification, email, password_hash, association_id, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    user.name,
                    user.phone,
                    user.identification,
                    user.email,
                    password_hash,
                    user.association_id,
                    role_value,
                ),
            )
            return cur.lastrowid

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()

    def get_user_by_phone_or_identification(self, value: str) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE phone = %s OR identification = %s",
                (value, value),
            )
            return cur.fetchone()

    def verify_password(self, plain: str, hashed: str) -> bool:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest() == hashed

    def set_token(self, user_id: int) -> str:
        token = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE users SET auth_token = %s WHERE id = %s",
                (token, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Usuario no encontrado al asignar token")
            return token

    def get_user_by_token(self, token: str) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE auth_token = %s", (token,))
            return cur.fetchone()

    def update_user(self, user_id: int, data: UserUpdate) -> bool:
        fields = []
        values = []
        for attr in ["name", "phone", "identification", "email", "association_id", "role"]:
            value = getattr(data, attr, None)
            if value is not None:
                fields.append(f"{attr} = %s")
                values.append(value)
        if getattr(data, "password", None):
            fields.append("password_hash = %s")
            values.append(hashlib.sha256(data.password.encode("utf-8")).hexdigest())
        if not fields:
            return False
        values.append(user_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = %s",
                values,
            )
            return cur.rowcount > 0

    # Associations
    def create_association(self, association: Association) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO associations (name, latitude, longitude, department, municipality, vereda)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (
                    association.name,
                    association.latitude,
                    association.longitude,
                    association.department,
                    association.municipality,
                    association.vereda,
                ),
            )
            return cur.lastrowid

    def get_association(self, association_id: int) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM associations WHERE id = %s", (association_id,))
            return cur.fetchone()

    def update_association(self, association_id: int, data: AssociationUpdate) -> bool:
        fields = []
        values = []
        for attr in ["name", "latitude", "longitude", "department", "municipality", "vereda"]:
            value = getattr(data, attr, None)
            if value is not None:
                fields.append(f"{attr} = %s")
                values.append(value)
        if not fields:
            return False
        values.append(association_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE associations SET {', '.join(fields)} WHERE id = %s",
                values,
            )
            return cur.rowcount > 0

    def list_associations(self) -> List[dict]:
        """List association id, name and municipality (city)."""
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT id, name, municipality FROM associations ORDER BY name ASC;"
            )
            return cur.fetchall()

    # Logbooks
    def create_logbook(self, logbook: Logbook) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO logbooks (user_id, association_id, title, description, activity_date)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    logbook.user_id,
                    logbook.association_id,
                    logbook.title,
                    logbook.description,
                    logbook.activity_date,
                ),
            )
            return cur.lastrowid

    def update_logbook(self, logbook_id: int, data: LogbookUpdate) -> bool:
        fields = []
        values = []
        if data.title is not None:
            fields.append("title = %s")
            values.append(data.title)
        if data.description is not None:
            fields.append("description = %s")
            values.append(data.description)
        if data.activity_date is not None:
            fields.append("activity_date = %s")
            values.append(data.activity_date)
        if data.association_id is not None:
            fields.append("association_id = %s")
            values.append(data.association_id)

        if not fields:
            return False

        values.append(logbook_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE logbooks SET {', '.join(fields)} WHERE id = %s",
                values,
            )
            return cur.rowcount > 0

    def delete_logbook(self, logbook_id: int) -> bool:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM logbooks WHERE id = %s", (logbook_id,))
            return cur.rowcount > 0

    def get_logbook(self, logbook_id: int) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT l.*, a.name AS association_name
                FROM logbooks l
                LEFT JOIN associations a ON l.association_id = a.id
                WHERE l.id = %s
                """,
                (logbook_id,),
            )
            return cur.fetchone()

    def list_logbooks_by_user(
        self, user_id: int, start_date: Optional[date], end_date: Optional[date]
    ) -> List[dict]:
        return self.list_logbooks(user_id=user_id, association_id=None, start_date=start_date, end_date=end_date)

    def list_logbooks(
        self,
        user_id: Optional[int],
        association_id: Optional[int],
        start_date: Optional[date],
        end_date: Optional[date],
        page: int = 1,
        page_size: int = 50,
    ) -> List[dict]:
        query = "SELECT * FROM logbooks WHERE 1=1"
        params: List = []
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        if association_id is not None:
            query += " AND association_id = %s"
            params.append(association_id)
        if start_date:
            query += " AND activity_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND activity_date <= %s"
            params.append(end_date)

        offset = (page - 1) * page_size
        query = (
            "SELECT l.*, a.name AS association_name "
            "FROM (" + query + " ORDER BY activity_date DESC LIMIT %s OFFSET %s) l "
            "LEFT JOIN associations a ON l.association_id = a.id "
        )
        params.extend([page_size, offset])
        with get_db_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    # Conversations (chat con IA)
    def add_chat_message(self, session_id: str, user_id: int, role: str, content: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (session_id, user_id, role, content),
            )

    def get_chat_history(self, session_id: str, user_id: int, limit: int = 10) -> List[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT role, content FROM conversations
                WHERE session_id = %s AND user_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (session_id, user_id, limit),
            )
            rows = cur.fetchall()
        return list(reversed(rows))
