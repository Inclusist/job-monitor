import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getJobs, hideJob, runMatching } from '../services/jobs';

interface JobsFilters {
  priority?: string;
  status?: string;
  min_score?: number;
}

export function useJobs(filters: JobsFilters = {}) {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => getJobs(filters),
  });
}

export function useHideJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: hideJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useRunMatching() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: runMatching,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      // Refetch matching-status after a short delay so the background thread
      // has time to set status='running', which activates polling
      queryClient.invalidateQueries({ queryKey: ['matching-status'] });
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['matching-status'] });
      }, 500);
    },
  });
}
