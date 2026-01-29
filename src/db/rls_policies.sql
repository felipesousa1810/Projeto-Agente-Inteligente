-- RLS Policies for Agente de Atendimento
-- Strategy:
-- 1. Service Role (Backend) bypasses RLS automatically.
-- 2. Authenticated Users (Dashboard/Admins) can VIEW data.
-- 3. Anonymous/Public has NO access.

-- Customers Table
CREATE POLICY "Enable read access for authenticated users" ON "public"."customers"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (true);

-- Appointments Table
CREATE POLICY "Enable read access for authenticated users" ON "public"."appointments"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (true);

-- Messages Table
CREATE POLICY "Enable read access for authenticated users" ON "public"."messages"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (true);

-- Dead Letter Queue
CREATE POLICY "Enable read access for authenticated users" ON "public"."dead_letter_queue"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (true);
