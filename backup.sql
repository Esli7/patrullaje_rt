--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+2)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg110+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: patrol_user
--

CREATE SCHEMA tiger;


ALTER SCHEMA tiger OWNER TO patrol_user;

--
-- Name: tiger_data; Type: SCHEMA; Schema: -; Owner: patrol_user
--

CREATE SCHEMA tiger_data;


ALTER SCHEMA tiger_data OWNER TO patrol_user;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: patrol_user
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO patrol_user;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: patrol_user
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


--
-- Name: crear_particion_ubicacion(integer, integer); Type: FUNCTION; Schema: public; Owner: patrol_user
--

CREATE FUNCTION public.crear_particion_ubicacion(p_anio integer, p_mes integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
  inicio DATE := make_date(p_anio, p_mes, 1);
  fin    DATE := (make_date(p_anio, p_mes, 1) + INTERVAL '1 month')::date;
  part_name TEXT := format('ubicacion_%s_%s', to_char(inicio,'YYYY'), to_char(inicio,'MM'));
BEGIN
  IF to_regclass(part_name) IS NULL THEN
    EXECUTE format($fmt$
      CREATE TABLE %I PARTITION OF ubicacion
      FOR VALUES FROM (%L) TO (%L);
      CREATE INDEX idx_%I_patrulla ON %I (patrulla_id);
      CREATE INDEX idx_%I_ts       ON %I (ts DESC);
      CREATE INDEX idx_%I_geom     ON %I USING GIST (geom);
      CREATE TRIGGER tg_%I_append_only
        BEFORE UPDATE OR DELETE ON %I
        FOR EACH STATEMENT EXECUTE FUNCTION forbid_update_delete();
    $fmt$, part_name, inicio, fin,
          part_name, part_name,
          part_name, part_name,
          part_name, part_name,
          part_name, part_name);
  END IF;
END;
$_$;


ALTER FUNCTION public.crear_particion_ubicacion(p_anio integer, p_mes integer) OWNER TO patrol_user;

--
-- Name: forbid_update_delete(); Type: FUNCTION; Schema: public; Owner: patrol_user
--

CREATE FUNCTION public.forbid_update_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  RAISE EXCEPTION 'Tabla append-only: operaciones % no permitidas en %', TG_OP, TG_TABLE_NAME;
END;
$$;


ALTER FUNCTION public.forbid_update_delete() OWNER TO patrol_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alerta; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.alerta (
    id bigint NOT NULL,
    patrulla_id integer,
    geocerca_id integer,
    tipo character varying(40) NOT NULL,
    severidad character varying(15) DEFAULT 'media'::character varying,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    detalle jsonb
);


ALTER TABLE public.alerta OWNER TO patrol_user;

--
-- Name: alerta_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.alerta_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerta_id_seq OWNER TO patrol_user;

--
-- Name: alerta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.alerta_id_seq OWNED BY public.alerta.id;


--
-- Name: asignacion_patrulla; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.asignacion_patrulla (
    id bigint NOT NULL,
    patrulla_id integer NOT NULL,
    operador_id integer,
    dispositivo_id integer,
    turno_id integer,
    inicio timestamp with time zone DEFAULT now() NOT NULL,
    fin timestamp with time zone,
    estado character varying(20) DEFAULT 'activa'::character varying
);


ALTER TABLE public.asignacion_patrulla OWNER TO patrol_user;

--
-- Name: asignacion_patrulla_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.asignacion_patrulla_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asignacion_patrulla_id_seq OWNER TO patrol_user;

--
-- Name: asignacion_patrulla_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.asignacion_patrulla_id_seq OWNED BY public.asignacion_patrulla.id;


--
-- Name: dispositivo; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.dispositivo (
    id integer NOT NULL,
    patrulla_id integer,
    identificador character varying(100) NOT NULL,
    so character varying(30),
    version_app character varying(30),
    activo boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.dispositivo OWNER TO patrol_user;

--
-- Name: dispositivo_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.dispositivo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dispositivo_id_seq OWNER TO patrol_user;

--
-- Name: dispositivo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.dispositivo_id_seq OWNED BY public.dispositivo.id;


--
-- Name: geocerca; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.geocerca (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    tipo character varying(30) DEFAULT 'operativa'::character varying,
    area public.geography(Polygon,4326) NOT NULL,
    activa boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.geocerca OWNER TO patrol_user;

--
-- Name: geocerca_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.geocerca_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.geocerca_id_seq OWNER TO patrol_user;

--
-- Name: geocerca_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.geocerca_id_seq OWNED BY public.geocerca.id;


--
-- Name: operador; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.operador (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    email character varying(150),
    telefono character varying(30),
    estado character varying(20) DEFAULT 'activo'::character varying,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.operador OWNER TO patrol_user;

--
-- Name: operador_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.operador_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.operador_id_seq OWNER TO patrol_user;

--
-- Name: operador_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.operador_id_seq OWNED BY public.operador.id;


--
-- Name: operador_rol; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.operador_rol (
    operador_id integer NOT NULL,
    rol_id integer NOT NULL
);


ALTER TABLE public.operador_rol OWNER TO patrol_user;

--
-- Name: patrulla; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.patrulla (
    id integer NOT NULL,
    codigo character varying(20) NOT NULL,
    alias character varying(50),
    activo boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    placa character varying(64),
    is_activa boolean DEFAULT true NOT NULL
);


ALTER TABLE public.patrulla OWNER TO patrol_user;

--
-- Name: patrulla_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.patrulla_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patrulla_id_seq OWNER TO patrol_user;

--
-- Name: patrulla_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.patrulla_id_seq OWNED BY public.patrulla.id;


--
-- Name: rol; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.rol (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion text
);


ALTER TABLE public.rol OWNER TO patrol_user;

--
-- Name: rol_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.rol_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rol_id_seq OWNER TO patrol_user;

--
-- Name: rol_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.rol_id_seq OWNED BY public.rol.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.roles (
    id smallint NOT NULL,
    code text NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.roles OWNER TO patrol_user;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.roles_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO patrol_user;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: turno_guardia; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.turno_guardia (
    id integer NOT NULL,
    nombre character varying(50) NOT NULL,
    inicio timestamp with time zone NOT NULL,
    fin timestamp with time zone NOT NULL
);


ALTER TABLE public.turno_guardia OWNER TO patrol_user;

--
-- Name: turno_guardia_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.turno_guardia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.turno_guardia_id_seq OWNER TO patrol_user;

--
-- Name: turno_guardia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.turno_guardia_id_seq OWNED BY public.turno_guardia.id;


--
-- Name: ubicacion; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.ubicacion (
    id bigint NOT NULL,
    patrulla_id integer NOT NULL,
    dispositivo_id integer,
    battery_pct smallint,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    geom public.geography(Point,4326) NOT NULL,
    CONSTRAINT ubicacion_battery_pct_check CHECK (((battery_pct >= 0) AND (battery_pct <= 100)))
)
PARTITION BY RANGE (ts);


ALTER TABLE public.ubicacion OWNER TO patrol_user;

--
-- Name: ubicacion_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.ubicacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ubicacion_id_seq OWNER TO patrol_user;

--
-- Name: ubicacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.ubicacion_id_seq OWNED BY public.ubicacion.id;


--
-- Name: ubicacion_2025_09; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.ubicacion_2025_09 (
    id bigint DEFAULT nextval('public.ubicacion_id_seq'::regclass) NOT NULL,
    patrulla_id integer NOT NULL,
    dispositivo_id integer,
    battery_pct smallint,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    geom public.geography(Point,4326) NOT NULL,
    CONSTRAINT ubicacion_battery_pct_check CHECK (((battery_pct >= 0) AND (battery_pct <= 100)))
);


ALTER TABLE public.ubicacion_2025_09 OWNER TO patrol_user;

--
-- Name: ubicacion_2025_10; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.ubicacion_2025_10 (
    id bigint DEFAULT nextval('public.ubicacion_id_seq'::regclass) NOT NULL,
    patrulla_id integer NOT NULL,
    dispositivo_id integer,
    battery_pct smallint,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    geom public.geography(Point,4326) NOT NULL,
    CONSTRAINT ubicacion_battery_pct_check CHECK (((battery_pct >= 0) AND (battery_pct <= 100)))
);


ALTER TABLE public.ubicacion_2025_10 OWNER TO patrol_user;

--
-- Name: ubicaciones; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.ubicaciones (
    id bigint NOT NULL,
    nombre text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.ubicaciones OWNER TO patrol_user;

--
-- Name: ubicaciones_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.ubicaciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ubicaciones_id_seq OWNER TO patrol_user;

--
-- Name: ubicaciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.ubicaciones_id_seq OWNED BY public.ubicaciones.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.user_roles (
    user_id bigint NOT NULL,
    role_id smallint NOT NULL
);


ALTER TABLE public.user_roles OWNER TO patrol_user;

--
-- Name: users; Type: TABLE; Schema: public; Owner: patrol_user
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO patrol_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: patrol_user
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO patrol_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: patrol_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: v_ultima_ubicacion; Type: VIEW; Schema: public; Owner: patrol_user
--

CREATE VIEW public.v_ultima_ubicacion AS
 SELECT DISTINCT ON (patrulla_id) id,
    patrulla_id,
    dispositivo_id,
    battery_pct,
    ts,
    geom
   FROM public.ubicacion u
  ORDER BY patrulla_id, ts DESC;


ALTER VIEW public.v_ultima_ubicacion OWNER TO patrol_user;

--
-- Name: ubicacion_2025_09; Type: TABLE ATTACH; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion ATTACH PARTITION public.ubicacion_2025_09 FOR VALUES FROM ('2025-09-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');


--
-- Name: ubicacion_2025_10; Type: TABLE ATTACH; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion ATTACH PARTITION public.ubicacion_2025_10 FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2025-11-01 00:00:00+00');


--
-- Name: alerta id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.alerta ALTER COLUMN id SET DEFAULT nextval('public.alerta_id_seq'::regclass);


--
-- Name: asignacion_patrulla id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla ALTER COLUMN id SET DEFAULT nextval('public.asignacion_patrulla_id_seq'::regclass);


--
-- Name: dispositivo id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.dispositivo ALTER COLUMN id SET DEFAULT nextval('public.dispositivo_id_seq'::regclass);


--
-- Name: geocerca id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.geocerca ALTER COLUMN id SET DEFAULT nextval('public.geocerca_id_seq'::regclass);


--
-- Name: operador id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador ALTER COLUMN id SET DEFAULT nextval('public.operador_id_seq'::regclass);


--
-- Name: patrulla id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.patrulla ALTER COLUMN id SET DEFAULT nextval('public.patrulla_id_seq'::regclass);


--
-- Name: rol id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.rol ALTER COLUMN id SET DEFAULT nextval('public.rol_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: turno_guardia id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.turno_guardia ALTER COLUMN id SET DEFAULT nextval('public.turno_guardia_id_seq'::regclass);


--
-- Name: ubicacion id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion ALTER COLUMN id SET DEFAULT nextval('public.ubicacion_id_seq'::regclass);


--
-- Name: ubicaciones id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicaciones ALTER COLUMN id SET DEFAULT nextval('public.ubicaciones_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alerta; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.alerta (id, patrulla_id, geocerca_id, tipo, severidad, ts, detalle) FROM stdin;
\.


--
-- Data for Name: asignacion_patrulla; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.asignacion_patrulla (id, patrulla_id, operador_id, dispositivo_id, turno_id, inicio, fin, estado) FROM stdin;
\.


--
-- Data for Name: dispositivo; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.dispositivo (id, patrulla_id, identificador, so, version_app, activo, created_at) FROM stdin;
\.


--
-- Data for Name: geocerca; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.geocerca (id, nombre, descripcion, tipo, area, activa, created_at) FROM stdin;
\.


--
-- Data for Name: operador; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.operador (id, nombre, email, telefono, estado, created_at) FROM stdin;
1	Admin	admin@gmail.com	\N	activo	2025-09-23 07:22:13.155711+00
\.


--
-- Data for Name: operador_rol; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.operador_rol (operador_id, rol_id) FROM stdin;
1	1
\.


--
-- Data for Name: patrulla; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.patrulla (id, codigo, alias, activo, created_at, placa, is_activa) FROM stdin;
1	P-001	Z6-Alpha	t	2025-09-14 03:43:33.60754+00	\N	t
\.


--
-- Data for Name: rol; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.rol (id, nombre, descripcion) FROM stdin;
1	admin	Administrador del sistema
2	supervisor	Supervisor de operaciones
3	operador	Operador de monitoreo
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.roles (id, code, name) FROM stdin;
1	admin	Administrador
2	operador	Operador
411	patrullero	Patrullero
412	usuario	Usuario
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: turno_guardia; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.turno_guardia (id, nombre, inicio, fin) FROM stdin;
\.


--
-- Data for Name: ubicacion_2025_09; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.ubicacion_2025_09 (id, patrulla_id, dispositivo_id, battery_pct, ts, geom) FROM stdin;
1	1	\N	92	2025-09-14 03:43:47.172246+00	0101000020E6100000BC0512143FA256C07DD0B359F5392D40
\.


--
-- Data for Name: ubicacion_2025_10; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.ubicacion_2025_10 (id, patrulla_id, dispositivo_id, battery_pct, ts, geom) FROM stdin;
\.


--
-- Data for Name: ubicaciones; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.ubicaciones (id, nombre, lat, lng, activo, created_at, updated_at) FROM stdin;
8	P-Chinautla Z6	14.7192	-90.4997	t	2025-09-27 04:15:02.146755+00	2025-09-27 04:15:02.146755+00
7	P-Chinautla Z6	14.776111	-90.587222	t	2025-09-27 03:57:22.014739+00	2025-09-27 07:33:06.836823+00
9	P-007 Chinautla	14.7188	-90.5012	t	2025-09-27 11:29:38.504082+00	2025-09-27 11:31:30.82079+00
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.user_roles (user_id, role_id) FROM stdin;
4	1
13	2
17	411
16	412
12	411
7	412
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: patrol_user
--

COPY public.users (id, email, password_hash, is_active, created_at, updated_at) FROM stdin;
4	admin@gmail.com	pbkdf2:sha256:1000000$Z2S9DmBtpgvBJd5t$5357f387434822f4015d8ac555ba543e2754e5d749dbfac5eb8fc7a93d2b6826	t	2025-09-22 03:11:06.105359+00	2025-09-22 03:11:06.105359+00
13	demo@acme.com	pbkdf2:sha256:1000000$1Zk4SRankPNAhagl$fc453bf8a79bddd5bfc1963dafa498801f4708cf8e0dc7ee77c8a8362e6f37d7	t	2025-09-26 03:19:40.61852+00	2025-09-27 04:41:12.394849+00
16	juan2@pnc.gob.gt	pbkdf2:sha256:1000000$hnXE6fNOTWqtXJZg$006423e39d1afc0ac543045713e1450508143fe4c34fcc1a226a7114e0a25b38	t	2025-09-29 23:38:53.533333+00	2025-10-01 14:43:46.833922+00
12	rol2@gmail.com	pbkdf2:sha256:1000000$P8iPcSbFqzjx69KI$a60c78140b198776989c2d2f3151893d16a57758417b13e4c8c00871a4e1e19b	t	2025-09-24 20:50:39.996038+00	2025-10-01 14:44:26.20204+00
7	editar3@gmail.com	pbkdf2:sha256:1000000$iOyNSb8vIoi6aelC$e1ccb3d3de596c256175e47b062c073aef0556541a28204e4819cc245ec4971d	t	2025-09-23 05:47:31.493545+00	2025-10-01 14:44:31.723617+00
17	prueba@gmail.com	pbkdf2:sha256:1000000$PyS2yg0DJTt87Nic$69cb8cc909e89e5c0268973a5605378cc76245b181faeca0717808fdcb8f01b5	t	2025-10-01 14:08:24.183303+00	2025-10-01 14:45:48.542631+00
\.


--
-- Data for Name: geocode_settings; Type: TABLE DATA; Schema: tiger; Owner: patrol_user
--

COPY tiger.geocode_settings (name, setting, unit, category, short_desc) FROM stdin;
\.


--
-- Data for Name: pagc_gaz; Type: TABLE DATA; Schema: tiger; Owner: patrol_user
--

COPY tiger.pagc_gaz (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_lex; Type: TABLE DATA; Schema: tiger; Owner: patrol_user
--

COPY tiger.pagc_lex (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_rules; Type: TABLE DATA; Schema: tiger; Owner: patrol_user
--

COPY tiger.pagc_rules (id, rule, is_custom) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: patrol_user
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: patrol_user
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: alerta_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.alerta_id_seq', 1, false);


--
-- Name: asignacion_patrulla_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.asignacion_patrulla_id_seq', 1, false);


--
-- Name: dispositivo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.dispositivo_id_seq', 1, false);


--
-- Name: geocerca_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.geocerca_id_seq', 1, false);


--
-- Name: operador_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.operador_id_seq', 2, true);


--
-- Name: patrulla_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.patrulla_id_seq', 1, true);


--
-- Name: rol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.rol_id_seq', 3, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.roles_id_seq', 496, true);


--
-- Name: turno_guardia_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.turno_guardia_id_seq', 1, false);


--
-- Name: ubicacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.ubicacion_id_seq', 1, true);


--
-- Name: ubicaciones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.ubicaciones_id_seq', 9, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: patrol_user
--

SELECT pg_catalog.setval('public.users_id_seq', 17, true);


--
-- Name: topology_id_seq; Type: SEQUENCE SET; Schema: topology; Owner: patrol_user
--

SELECT pg_catalog.setval('topology.topology_id_seq', 1, false);


--
-- Name: alerta alerta_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.alerta
    ADD CONSTRAINT alerta_pkey PRIMARY KEY (id);


--
-- Name: asignacion_patrulla asignacion_patrulla_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla
    ADD CONSTRAINT asignacion_patrulla_pkey PRIMARY KEY (id);


--
-- Name: dispositivo dispositivo_identificador_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.dispositivo
    ADD CONSTRAINT dispositivo_identificador_key UNIQUE (identificador);


--
-- Name: dispositivo dispositivo_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.dispositivo
    ADD CONSTRAINT dispositivo_pkey PRIMARY KEY (id);


--
-- Name: geocerca geocerca_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.geocerca
    ADD CONSTRAINT geocerca_pkey PRIMARY KEY (id);


--
-- Name: operador operador_email_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador
    ADD CONSTRAINT operador_email_key UNIQUE (email);


--
-- Name: operador operador_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador
    ADD CONSTRAINT operador_pkey PRIMARY KEY (id);


--
-- Name: operador_rol operador_rol_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador_rol
    ADD CONSTRAINT operador_rol_pkey PRIMARY KEY (operador_id, rol_id);


--
-- Name: patrulla patrulla_codigo_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.patrulla
    ADD CONSTRAINT patrulla_codigo_key UNIQUE (codigo);


--
-- Name: patrulla patrulla_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.patrulla
    ADD CONSTRAINT patrulla_pkey PRIMARY KEY (id);


--
-- Name: rol rol_nombre_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_nombre_key UNIQUE (nombre);


--
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id);


--
-- Name: roles roles_code_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: turno_guardia turno_guardia_nombre_inicio_fin_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.turno_guardia
    ADD CONSTRAINT turno_guardia_nombre_inicio_fin_key UNIQUE (nombre, inicio, fin);


--
-- Name: turno_guardia turno_guardia_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.turno_guardia
    ADD CONSTRAINT turno_guardia_pkey PRIMARY KEY (id);


--
-- Name: ubicacion ubicacion_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion
    ADD CONSTRAINT ubicacion_pkey PRIMARY KEY (id, ts);


--
-- Name: ubicacion_2025_09 ubicacion_2025_09_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion_2025_09
    ADD CONSTRAINT ubicacion_2025_09_pkey PRIMARY KEY (id, ts);


--
-- Name: ubicacion_2025_10 ubicacion_2025_10_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicacion_2025_10
    ADD CONSTRAINT ubicacion_2025_10_pkey PRIMARY KEY (id, ts);


--
-- Name: ubicaciones ubicaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.ubicaciones
    ADD CONSTRAINT ubicaciones_pkey PRIMARY KEY (id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_alerta_tipo; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_alerta_tipo ON public.alerta USING btree (tipo);


--
-- Name: idx_alerta_ts; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_alerta_ts ON public.alerta USING btree (ts DESC);


--
-- Name: idx_asig_patrulla; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_asig_patrulla ON public.asignacion_patrulla USING btree (patrulla_id, estado);


--
-- Name: idx_geo_area; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_geo_area ON public.geocerca USING gist (area);


--
-- Name: idx_ubicacion_2025_09_geom; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_09_geom ON public.ubicacion_2025_09 USING gist (geom);


--
-- Name: idx_ubicacion_2025_09_patrulla; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_09_patrulla ON public.ubicacion_2025_09 USING btree (patrulla_id);


--
-- Name: idx_ubicacion_2025_09_ts; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_09_ts ON public.ubicacion_2025_09 USING btree (ts DESC);


--
-- Name: idx_ubicacion_2025_10_geom; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_10_geom ON public.ubicacion_2025_10 USING gist (geom);


--
-- Name: idx_ubicacion_2025_10_patrulla; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_10_patrulla ON public.ubicacion_2025_10 USING btree (patrulla_id);


--
-- Name: idx_ubicacion_2025_10_ts; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicacion_2025_10_ts ON public.ubicacion_2025_10 USING btree (ts DESC);


--
-- Name: idx_ubicaciones_activo; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicaciones_activo ON public.ubicaciones USING btree (activo);


--
-- Name: idx_ubicaciones_lat; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicaciones_lat ON public.ubicaciones USING btree (lat);


--
-- Name: idx_ubicaciones_lng; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicaciones_lng ON public.ubicaciones USING btree (lng);


--
-- Name: idx_ubicaciones_lng_lat; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicaciones_lng_lat ON public.ubicaciones USING btree (lng, lat);


--
-- Name: idx_ubicaciones_updated_at; Type: INDEX; Schema: public; Owner: patrol_user
--

CREATE INDEX idx_ubicaciones_updated_at ON public.ubicaciones USING btree (updated_at);


--
-- Name: ubicacion_2025_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: patrol_user
--

ALTER INDEX public.ubicacion_pkey ATTACH PARTITION public.ubicacion_2025_09_pkey;


--
-- Name: ubicacion_2025_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: patrol_user
--

ALTER INDEX public.ubicacion_pkey ATTACH PARTITION public.ubicacion_2025_10_pkey;


--
-- Name: ubicacion_2025_09 tg_ubicacion_2025_09_append_only; Type: TRIGGER; Schema: public; Owner: patrol_user
--

CREATE TRIGGER tg_ubicacion_2025_09_append_only BEFORE DELETE OR UPDATE ON public.ubicacion_2025_09 FOR EACH STATEMENT EXECUTE FUNCTION public.forbid_update_delete();


--
-- Name: ubicacion_2025_10 tg_ubicacion_2025_10_append_only; Type: TRIGGER; Schema: public; Owner: patrol_user
--

CREATE TRIGGER tg_ubicacion_2025_10_append_only BEFORE DELETE OR UPDATE ON public.ubicacion_2025_10 FOR EACH STATEMENT EXECUTE FUNCTION public.forbid_update_delete();


--
-- Name: ubicacion tg_ubicacion_append_only; Type: TRIGGER; Schema: public; Owner: patrol_user
--

CREATE TRIGGER tg_ubicacion_append_only BEFORE DELETE OR UPDATE ON public.ubicacion FOR EACH STATEMENT EXECUTE FUNCTION public.forbid_update_delete();


--
-- Name: alerta alerta_geocerca_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.alerta
    ADD CONSTRAINT alerta_geocerca_id_fkey FOREIGN KEY (geocerca_id) REFERENCES public.geocerca(id) ON DELETE SET NULL;


--
-- Name: alerta alerta_patrulla_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.alerta
    ADD CONSTRAINT alerta_patrulla_id_fkey FOREIGN KEY (patrulla_id) REFERENCES public.patrulla(id) ON DELETE SET NULL;


--
-- Name: asignacion_patrulla asignacion_patrulla_dispositivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla
    ADD CONSTRAINT asignacion_patrulla_dispositivo_id_fkey FOREIGN KEY (dispositivo_id) REFERENCES public.dispositivo(id) ON DELETE SET NULL;


--
-- Name: asignacion_patrulla asignacion_patrulla_operador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla
    ADD CONSTRAINT asignacion_patrulla_operador_id_fkey FOREIGN KEY (operador_id) REFERENCES public.operador(id) ON DELETE SET NULL;


--
-- Name: asignacion_patrulla asignacion_patrulla_patrulla_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla
    ADD CONSTRAINT asignacion_patrulla_patrulla_id_fkey FOREIGN KEY (patrulla_id) REFERENCES public.patrulla(id) ON DELETE CASCADE;


--
-- Name: asignacion_patrulla asignacion_patrulla_turno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.asignacion_patrulla
    ADD CONSTRAINT asignacion_patrulla_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.turno_guardia(id) ON DELETE SET NULL;


--
-- Name: dispositivo dispositivo_patrulla_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.dispositivo
    ADD CONSTRAINT dispositivo_patrulla_id_fkey FOREIGN KEY (patrulla_id) REFERENCES public.patrulla(id) ON DELETE SET NULL;


--
-- Name: operador_rol operador_rol_operador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador_rol
    ADD CONSTRAINT operador_rol_operador_id_fkey FOREIGN KEY (operador_id) REFERENCES public.operador(id) ON DELETE CASCADE;


--
-- Name: operador_rol operador_rol_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.operador_rol
    ADD CONSTRAINT operador_rol_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id) ON DELETE CASCADE;


--
-- Name: ubicacion ubicacion_dispositivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE public.ubicacion
    ADD CONSTRAINT ubicacion_dispositivo_id_fkey FOREIGN KEY (dispositivo_id) REFERENCES public.dispositivo(id) ON DELETE SET NULL;


--
-- Name: ubicacion ubicacion_patrulla_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE public.ubicacion
    ADD CONSTRAINT ubicacion_patrulla_id_fkey FOREIGN KEY (patrulla_id) REFERENCES public.patrulla(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: patrol_user
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

