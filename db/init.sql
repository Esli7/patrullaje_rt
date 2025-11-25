-- ============================================
-- ACTUALIZACIÓN DE ESTRUCTURA Y NORMALIZACIÓN DE NIP
-- ============================================

-- 1️⃣ Columns (idempotentes)
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS nombre VARCHAR(150),
  ADD COLUMN IF NOT EXISTS nip    VARCHAR(20);

-- 2️⃣ Migración de datos heredados
-- Convierte formatos antiguos (ej. A-789 → 00789-A)
-- y limpia cualquier valor inválido antes de agregar el CHECK
-- ============================================
-- Paso 1: Convertir L-### → 00###-L
UPDATE public.users
SET nip = LPAD(regexp_replace(nip, '^[A-Z]-([0-9]+)$', '\1'), 5, '0')
         || '-' ||
         regexp_replace(nip, '^([A-Z]).*$', '\1')
WHERE nip ~ '^[A-Z]-[0-9]+$';

-- Paso 2: Forzar mayúsculas en todos los NIP existentes
UPDATE public.users
SET nip = UPPER(nip)
WHERE nip IS NOT NULL;

-- Paso 3: Limpiar NIP que no cumplen el formato #####-L
UPDATE public.users
SET nip = NULL
WHERE nip IS NOT NULL
  AND NOT (nip ~ '^[0-9]{5}-[A-Z]$');

-- 3️⃣ Unicidad parcial (permite NULL)
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_nip
  ON public.users (nip) WHERE nip IS NOT NULL;

-- 4️⃣ CHECK de formato (permite NULL)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='users' AND constraint_name='ck_users_nip_format'
  ) THEN
    ALTER TABLE public.users
      ADD CONSTRAINT ck_users_nip_format
      CHECK (nip ~ '^[0-9]{5}-[A-Z]$' OR nip IS NULL);
  END IF;
END
$$;

-- 5️⃣ Trigger: NIP siempre en mayúsculas
CREATE OR REPLACE FUNCTION users_nip_uppercase_fn()
RETURNS trigger AS $$
BEGIN
  IF NEW.nip IS NOT NULL THEN
    NEW.nip := UPPER(NEW.nip);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_nip_uppercase ON public.users;
CREATE TRIGGER trg_users_nip_uppercase
BEFORE INSERT OR UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION users_nip_uppercase_fn();

-- ============================================
-- FIN BLOQUE NORMALIZACIÓN DE NIP
-- ============================================
