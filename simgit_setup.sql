-- ========================================================================================
-- OpenDAV V1.0: SimGit Enterprise Cloud Setup Script
-- Paste this entire script into your Supabase SQL Editor and click RUN.
-- This script provisions the team database, security triggers, and S3 storage.
-- ========================================================================================

-- 1. Create the Team Members Table (Role-Based Access Control)
CREATE TABLE IF NOT EXISTS public.team_members (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Enable Row Level Security
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;

-- 2. Grant Access to Authenticated Users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON public.team_members TO authenticated;

-- 3. Security Policies for team_members (Safely recreate)
DROP POLICY IF EXISTS "Admins can do everything" ON public.team_members;
DROP POLICY IF EXISTS "Approved users can read team" ON public.team_members;
DROP POLICY IF EXISTS "Users can read own row" ON public.team_members;

CREATE POLICY "Admins can do everything" ON public.team_members
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.team_members tm WHERE tm.id = auth.uid() AND tm.role = 'admin'));

CREATE POLICY "Approved users can read team" ON public.team_members
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.team_members tm WHERE tm.id = auth.uid() AND tm.role IN ('admin', 'approved')));

CREATE POLICY "Users can read own row" ON public.team_members
    FOR SELECT TO authenticated
    USING (id = auth.uid());

-- 4. Auto-Admin Trigger Function
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
DECLARE
    user_count INT;
BEGIN
    -- Check if this is the very first user on the server
    SELECT COUNT(*) INTO user_count FROM public.team_members;
    
    IF user_count = 0 THEN
        INSERT INTO public.team_members (id, email, role) VALUES (new.id, new.email, 'admin');
    ELSE
        INSERT INTO public.team_members (id, email, role) VALUES (new.id, new.email, 'pending');
    END IF;
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Bind Trigger to Auth Table
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created 
    AFTER INSERT ON auth.users 
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 5. Backfill Existing Users (For accounts created before this script ran)
DO $$
DECLARE
    first_user_id UUID;
    first_user_email TEXT;
BEGIN
    -- Grab the first person who ever signed up
    SELECT id, email INTO first_user_id, first_user_email 
    FROM auth.users 
    ORDER BY created_at ASC 
    LIMIT 1;

    -- Force them into the team_members table as 'admin'
    IF first_user_id IS NOT NULL THEN
        INSERT INTO public.team_members (id, email, role)
        VALUES (first_user_id, first_user_email, 'admin')
        ON CONFLICT (id) DO UPDATE SET role = 'admin';
    END IF;
    
    -- Sweep all other existing users into 'pending'
    INSERT INTO public.team_members (id, email, role)
    SELECT id, email, 'pending' FROM auth.users
    WHERE id != first_user_id
    ON CONFLICT (id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- 6. Provision the S3 Storage Bucket
INSERT INTO storage.buckets (id, name, public) 
VALUES ('opendav_assets', 'opendav_assets', false) 
ON CONFLICT (id) DO NOTHING;

-- 7. Helper Function for Cross-Schema Storage RLS
-- (Allows the Storage engine to securely check team roles in the public schema)
CREATE OR REPLACE FUNCTION public.is_simgit_approved() 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.team_members tm 
        WHERE tm.id = auth.uid() AND tm.role IN ('admin', 'approved')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.is_simgit_approved() TO authenticated;

-- 8. Lock Down the Storage Bucket (Zero-Trust Security)
DROP POLICY IF EXISTS "SimGit Enterprise Access" ON storage.objects;
CREATE POLICY "SimGit Enterprise Access" ON storage.objects
    FOR ALL TO authenticated
    USING (bucket_id = 'opendav_assets' AND public.is_simgit_approved())
    WITH CHECK (bucket_id = 'opendav_assets' AND public.is_simgit_approved());

-- Done! SimGit is now ready for production.
