import { getBooksSSR } from '@/lib/api-ssr';
import BooksClient from './BooksClient';

export const dynamic = 'force-dynamic';

export default async function BooksPage() {
  const data = await getBooksSSR({ page: 1, page_size: 20 });

  return (
    <BooksClient
      initialBooks={data.items || []}
      initialTotal={data.total || 0}
    />
  );
}
