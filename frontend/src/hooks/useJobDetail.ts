import { useQuery } from '@tanstack/react-query';
import { getJobDetail } from '../services/jobs';

export function useJobDetail(jobId: number | null) {
  return useQuery({
    queryKey: ['jobDetail', jobId],
    queryFn: () => getJobDetail(jobId!),
    enabled: jobId !== null,
    staleTime: 5 * 60 * 1000,
  });
}
