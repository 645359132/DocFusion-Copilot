import StateCardFrame from '@/components/StateCardFrame';

export default function ErrorStateCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return <StateCardFrame tone="error" badge="错误" title={title} description={description} />;
}