#!/usr/bin/perl
use strict;
use warnings;
use JSON::PP qw(encode_json decode_json);
use LoxBerry::System;

my $mode = shift(@ARGV) // 'list';

sub miniservers {
    # get_miniservers() returns a HASH keyed by the real LoxBerry
    # Miniserver number (1, 2, ...). Preserve that key explicitly so
    # the Web UI cannot accidentally turn hash key/value pairs into
    # fake list entries.
    my %ms = LoxBerry::System::get_miniservers();
    my @out;
    foreach my $msno (sort { $a <=> $b } keys %ms) {
        next unless ref($ms{$msno}) eq 'HASH';
        my %entry = %{ $ms{$msno} };
        $entry{'_msno'} = int($msno);
        push @out, \%entry;
    }
    return \@out;
}

if ($mode eq 'list') {
    my $ms = miniservers();
    print encode_json($ms);
    exit 0;
}

if ($mode eq 'send') {
    require LoxBerry::IO;
    my $msno = int(shift(@ARGV) // 0);
    my $port = int(shift(@ARGV) // 0);
    my $prefix = shift(@ARGV) // 'velux';
    die "Invalid Miniserver number\n" if $msno < 1;
    die "Invalid UDP port\n" if $port < 1 || $port > 65535;
    local $/;
    my $raw = <STDIN> // '{}';
    my $data = decode_json($raw);
    die "Expected JSON object\n" unless ref($data) eq 'HASH';
    my $count = 0;
    for my $key (sort keys %$data) {
        my $value = $data->{$key};
        if (ref($value)) { next; }
        $value = $value ? 1 : 0 if JSON::PP::is_bool($value);
        my %send = ($prefix . '.' . $key => $value);
        my $ok = LoxBerry::IO::msudp_send($msno, $port, undef, %send);
        die "UDP send failed for $key\n" unless defined $ok;
        $count++;
    }
    print $count;
    exit 0;
}

die "Unknown mode\n";
