-- Run this in your Supabase SQL Editor one more time.
-- This manually ensures you are in the table.
INSERT INTO public.team_members (id, email, role)
VALUES ('d03a8f02-6043-49f3-a5bb-016f27aba3ef', 'YOUR_EMAIL@GMAIL.COM', 'admin')
ON CONFLICT (id) DO UPDATE SET role = 'admin';

GRANT SELECT ON public.team_members TO authenticated;
