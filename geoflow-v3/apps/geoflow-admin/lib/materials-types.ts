export type CategoryItem = {
  id: number;
  name: string;
  slug: string;
  description: string;
  sort_order: number;
};

export type AuthorItem = {
  id: number;
  name: string;
  bio: string;
  email: string;
};

export type CategoryPayload = {
  name: string;
  slug?: string;
  description: string;
  sort_order: number;
};

export type AuthorPayload = {
  name: string;
  bio: string;
  email: string;
};
