@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        @include('admin.tasks._panel', ['standalone' => true])
    </div>
@endsection

@push('scripts')
    @include('admin.tasks._scripts')
@endpush
