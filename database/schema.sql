-- Crear base de datos (ejecutar como superusuario si es necesario)
-- CREATE DATABASE agrohub_families;

-- Usar la base de datos
-- \c agrohub_families;

-- Crear tabla de familias
CREATE TABLE IF NOT EXISTS families (
    id SERIAL PRIMARY KEY,
    nombre_jefe VARCHAR(100) NOT NULL,
    apellido_jefe VARCHAR(100) NOT NULL,
    cedula VARCHAR(20) UNIQUE NOT NULL,
    telefono VARCHAR(15) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    vereda VARCHAR(100) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    numero_integrantes VARCHAR(10),
    tipo_vivienda VARCHAR(50),
    actividad_economica VARCHAR(255),
    observaciones TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    sincronizado BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_families_cedula ON families(cedula);
CREATE INDEX IF NOT EXISTS idx_families_municipio ON families(municipio);
CREATE INDEX IF NOT EXISTS idx_families_vereda ON families(vereda);
CREATE INDEX IF NOT EXISTS idx_families_timestamp ON families(timestamp);
CREATE INDEX IF NOT EXISTS idx_families_sincronizado ON families(sincronizado);

-- Crear función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Crear trigger para actualizar updated_at
DROP TRIGGER IF EXISTS update_families_updated_at ON families;
CREATE TRIGGER update_families_updated_at
    BEFORE UPDATE ON families
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comentarios en la tabla
COMMENT ON TABLE families IS 'Tabla para almacenar información de familias rurales del proyecto AgroHub Magdalena';
COMMENT ON COLUMN families.cedula IS 'Cédula del jefe de familia - campo único';
COMMENT ON COLUMN families.timestamp IS 'Timestamp original del dispositivo móvil';
COMMENT ON COLUMN families.sincronizado IS 'Indica si los datos están sincronizados con el servidor';
COMMENT ON COLUMN families.created_at IS 'Fecha de creación del registro en el servidor';
COMMENT ON COLUMN families.updated_at IS 'Fecha de última actualización del registro';

-- ========================================
-- TABLAS DEL JUEGO INTERACTIVO
-- ========================================

-- Tabla de sesiones de juego
CREATE TABLE IF NOT EXISTS game_sessions (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'waiting',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    total_questions INTEGER DEFAULT 0,
    total_participants INTEGER DEFAULT 0
);

-- Trigger para actualizar updated_at en game_sessions
CREATE OR REPLACE FUNCTION update_game_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_game_sessions_updated_at
BEFORE UPDATE ON game_sessions
FOR EACH ROW
EXECUTE FUNCTION update_game_sessions_updated_at();

-- Tabla de participantes del juego
CREATE TABLE IF NOT EXISTS game_participants (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    user_id UUID,
    score INTEGER DEFAULT 0,
    tokens INTEGER DEFAULT 0,
    points_converted_to_tokens INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    total_answers INTEGER DEFAULT 0,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, email)
);

-- Trigger para game_participants
DROP TRIGGER IF EXISTS update_game_participants_updated_at ON game_participants;
CREATE TRIGGER update_game_participants_updated_at
    BEFORE UPDATE ON game_participants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Tabla de preguntas del juego
CREATE TABLE IF NOT EXISTS game_questions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_answer INTEGER NOT NULL,
    time_limit INTEGER DEFAULT 30,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    question_order INTEGER
);

-- Tabla de respuestas de los participantes
CREATE TABLE IF NOT EXISTS game_answers (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES game_participants(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES game_questions(id) ON DELETE CASCADE,
    answer INTEGER,
    is_correct BOOLEAN,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear trigger para actualizar 'updated_at' en 'game_sessions'
DROP TRIGGER IF EXISTS update_game_sessions_updated_at ON game_sessions;
CREATE TRIGGER update_game_sessions_updated_at
    BEFORE UPDATE ON game_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Crear función para actualizar tokens automáticamente basado en puntos
CREATE OR REPLACE FUNCTION calculate_tokens()
RETURNS TRIGGER AS $$
DECLARE
    points_available_for_tokens INTEGER;
    new_tokens_earned INTEGER;
BEGIN
    -- Puntos disponibles para convertir a tokens (puntos totales - puntos ya convertidos)
    points_available_for_tokens := NEW.score - NEW.points_converted_to_tokens;
    
    -- Calcular nuevos tokens que se pueden obtener
    new_tokens_earned := FLOOR(points_available_for_tokens / 300);
    
    -- Solo actualizar si hay nuevos tokens para ganar
    IF new_tokens_earned > 0 THEN
        -- Agregar los nuevos tokens
        NEW.tokens := NEW.tokens + new_tokens_earned;
        -- Actualizar los puntos que han sido convertidos
        NEW.points_converted_to_tokens := NEW.points_converted_to_tokens + (new_tokens_earned * 300);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para actualizar tokens cuando se actualice el score
DROP TRIGGER IF EXISTS update_tokens ON game_participants;
CREATE TRIGGER update_tokens
    BEFORE UPDATE ON game_participants
    FOR EACH ROW
    WHEN (OLD.score IS DISTINCT FROM NEW.score)
    EXECUTE FUNCTION calculate_tokens();

-- Crear trigger para actualizar tokens al insertar un nuevo participante
DROP TRIGGER IF EXISTS insert_tokens ON game_participants;
CREATE TRIGGER insert_tokens
    BEFORE INSERT ON game_participants
    FOR EACH ROW
    EXECUTE FUNCTION calculate_tokens();

-- Crear función para actualizar last_activity automáticamente
CREATE OR REPLACE FUNCTION update_last_activity_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_activity = CURRENT_TIMESTAMP;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Crear trigger para actualizar 'last_activity' en 'game_participants'
DROP TRIGGER IF EXISTS update_game_participants_last_activity ON game_participants;
CREATE TRIGGER update_game_participants_last_activity
    BEFORE UPDATE ON game_participants
    FOR EACH ROW
    EXECUTE FUNCTION update_last_activity_column();

-- Comentarios en las tablas del juego
COMMENT ON TABLE game_sessions IS 'Sesiones de juego interactivo';
COMMENT ON TABLE game_participants IS 'Participantes en cada sesión de juego';
COMMENT ON TABLE game_questions IS 'Preguntas enviadas durante el juego';
COMMENT ON TABLE game_answers IS 'Respuestas de los participantes a las preguntas';
COMMENT ON COLUMN game_sessions.status IS 'Estado del juego: waiting, standby, active, finished';
COMMENT ON COLUMN game_participants.email IS 'Email del participante (identificador único por sesión)';
COMMENT ON COLUMN game_participants.score IS 'Puntuación total del participante';
COMMENT ON COLUMN game_participants.tokens IS 'Tokens disponibles para redimir (se incrementan con puntos, se reducen al redimir)';
COMMENT ON COLUMN game_participants.points_converted_to_tokens IS 'Puntos que ya han sido convertidos a tokens (para evitar doble conteo)';
COMMENT ON COLUMN game_questions.options IS 'Opciones de respuesta en formato JSON';
COMMENT ON COLUMN game_answers.answered_at IS 'Fecha y hora en que el participante respondió';

-- ========================================
-- TABLA DE VOTACIONES DE FELICIDAD
-- ========================================

CREATE TABLE IF NOT EXISTS happiness_votes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    vote INTEGER NOT NULL CHECK (vote >= 1 AND vote <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para actualizar updated_at en happiness_votes
DROP TRIGGER IF EXISTS trigger_update_happiness_votes_updated_at ON happiness_votes;
CREATE OR REPLACE FUNCTION update_happiness_votes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_happiness_votes_updated_at
BEFORE UPDATE ON happiness_votes
FOR EACH ROW
EXECUTE FUNCTION update_happiness_votes_updated_at();

COMMENT ON TABLE happiness_votes IS 'Almacena las votaciones de felicidad de los usuarios';
COMMENT ON COLUMN happiness_votes.email IS 'Email del votante (único)';
COMMENT ON COLUMN happiness_votes.vote IS 'Voto de felicidad en una escala de 1 a 5';
