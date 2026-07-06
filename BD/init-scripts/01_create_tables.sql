CREATE TABLE IF NOT EXISTS department(
    id_department int            GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           varchar(128),
    full_name      text          NOT NULL
);

CREATE TABLE IF NOT EXISTS position(
    id_position int          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        varchar(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS training_type(
    id_type int          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    varchar(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS program(
    id_program       int          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_type          int          NOT NULL,
    program_code     int          NOT NULL UNIQUE,
    name             varchar(128) NOT NULL,
    time_to_complete time         NOT NULL,
    is_shown         boolean      NOT NULL,

    CONSTRAINT program_type_fk
        FOREIGN KEY (id_type)
        REFERENCES training_type(id_type)
        ON UPDATE SET NULL
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS topic(
    id_topic   int          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_program int          NOT NULL,
    name       varchar(128) NOT NULL,

    CONSTRAINT topic_program_fk
        FOREIGN KEY (id_program)
        REFERENCES program(id_program)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_material(
    id_learning_material int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_topic             int  NOT NULL,
    file_link            text NOT NULL,

    CONSTRAINT learning_mat_topic_fk
        FOREIGN KEY (id_topic)
        REFERENCES topic(id_topic)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question(
    id_question   int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_topic      int  NOT NULL,
    question_text text NOT NULL,
    is_verified   bool NOT NULL,

    CONSTRAINT question_topic_fk
        FOREIGN KEY (id_topic)
        REFERENCES topic(id_topic)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answer(
    id_answer    int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_question  int  NOT NULL,
    answer_text  text NOT NULL,
    is_correct   bool NOT NULL,

    CONSTRAINT answer_question_fk
        FOREIGN KEY (id_question)
        REFERENCES question(id_question)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS employee(
    id_employee        int         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_department       int,
    id_position         int,
    employee_number     int         NOT NULL UNIQUE,
    first_name          varchar(64) NOT NULL,
    last_name           varchar(64) NOT NULL,
    middle_name         varchar(64),
    email               varchar(254) NOT NULL UNIQUE,
    password_hash       varchar(255) NOT NULL,
    reset_token         varchar(255),
    reset_token_expiry  timestamp,

    CONSTRAINT employee_dep_fk
        FOREIGN KEY (id_department)
        REFERENCES department(id_department)
        ON UPDATE SET NULL
        ON DELETE SET NULL,

    CONSTRAINT employee_pos_fk
        FOREIGN KEY (id_position)
        REFERENCES position(id_position)
        ON UPDATE SET NULL
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notification(
     id          int       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
     id_employee int       NOT NULL,
     date        timestamp NOT NULL,
     is_viewed   bool      NOT NULL,

     CONSTRAINT notification_emp_fk
         FOREIGN KEY (id_employee)
          REFERENCES employee(id_employee)
             ON UPDATE CASCADE
             ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaint(
    id_complaint   int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_question    int  NOT NULL,
    complaint_text text NOT NULL,
    is_solved      bool NOT NULL,

    CONSTRAINT complaint_question_fk
        FOREIGN KEY (id_question)
        REFERENCES question(id_question)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS request(
    id_request       int           GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_employee      int           NOT NULL,
    id_topic         int           NOT NULL,
    message_text     varchar(1024) NOT NULL,
    ai_response_text text          NOT NULL,
    sequence_number  int           NOT NULL,

    CONSTRAINT request_employee_fk
        FOREIGN KEY (id_employee)
        REFERENCES employee(id_employee)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT request_topic_fk
        FOREIGN KEY (id_topic)
        REFERENCES topic(id_topic)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS program_completion(
    id_program_completion int       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_employee           int       NOT NULL,
    id_program            int       NOT NULL,
    start_date            timestamp NOT NULL,
    end_date              timestamp,

    CONSTRAINT program_completion_employee_fk
        FOREIGN KEY (id_employee)
        REFERENCES employee(id_employee)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT program_completion_program_fk
        FOREIGN KEY (id_program)
        REFERENCES program(id_program)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS material_study(
    id_program_completion int  NOT NULL,
    id_learning_material  int  NOT NULL,
    is_read               bool NOT NULL,

    CONSTRAINT material_study_pk
        PRIMARY KEY (id_program_completion, id_learning_material),

    CONSTRAINT material_study_program_completion_fk
        FOREIGN KEY (id_program_completion)
        REFERENCES program_completion(id_program_completion)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT material_study_learning_material_fk
        FOREIGN KEY (id_learning_material)
        REFERENCES learning_material(id_learning_material)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_completion(
    id_test_completion    int  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_program_completion int  NOT NULL,
    id_answer             int  NOT NULL,
    is_final_test         bool NOT NULL,

    CONSTRAINT test_completion_program_completion_fk
        FOREIGN KEY (id_program_completion)
        REFERENCES program_completion(id_program_completion)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT test_completion_answer_fk
        FOREIGN KEY (id_answer)
        REFERENCES answer(id_answer)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS literature (
    id_literature int          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          varchar(128) NOT NULL,
    material_link text         NOT NULL
);

CREATE TABLE IF NOT EXISTS program_literature (
    id_program_literature int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_program            int NOT NULL,
    id_literature         int NOT NULL,
    
    CONSTRAINT program_literature_program_fk
        FOREIGN KEY (id_program)
        REFERENCES program(id_program)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
        
    CONSTRAINT program_literature_literature_fk
        FOREIGN KEY (id_literature)
        REFERENCES literature(id_literature)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
        
    CONSTRAINT program_literature_unique UNIQUE (id_program, id_literature)
);