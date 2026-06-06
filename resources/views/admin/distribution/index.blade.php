@extends('admin.layouts.app')

@section('content')
    <div class="space-y-8 px-4 sm:px-0">
        @include('admin.distribution._panel', ['standalone' => true])
    </div>
@endsection
