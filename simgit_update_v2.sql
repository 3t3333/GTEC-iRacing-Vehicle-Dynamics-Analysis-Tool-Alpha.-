-- ========================================================================================
-- OpenDAV V2.0.1 Migration Script (For existing databases only)
-- If you previously installed OpenDAV 1.0, run this script to update your security policies.
-- ========================================================================================

GRANT SELECT, INSERT ON public.team_members TO authenticated;

DROP POLICY IF EXISTS "Users can auto-heal their own pending row" ON public.team_members;

CREATE POLICY "Users can auto-heal their own pending row" ON public.team_members
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = id::uuid AND role = 'pending');
