#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
my $q=CGI->new;
my $file=$q->param('file') // '';
$file =~ s/[^A-Za-z0-9_.-]//g;
my %ok=map { $_=>1 } qw(loxone_udp_inputs.txt loxone_udp_inputs.csv loxone_udp_commands.txt loxone_udp_commands.csv loxone_velux_export.xml);
if (!$ok{$file}) {
  print "Status: 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nUngültige Datei";
  exit;
}
my $base=$ENV{LBPDATADIR} || "/opt/loxberry/data/plugins/veluxactive";
my $path="$base/exports/$file";
if (!-f $path) {
  print "Status: 404 Not Found\r\nContent-Type: text/plain\r\n\r\nExport nicht gefunden";
  exit;
}
my $ctype = $file =~ /\.csv$/ ? 'text/csv; charset=utf-8' : ($file =~ /\.xml$/ ? 'application/xml; charset=utf-8' : 'text/plain; charset=utf-8');
print "Content-Type: $ctype\r\n";
print "Content-Disposition: attachment; filename=\"$file\"\r\n\r\n";
open my $fh,'<:raw',$path or die $!;
while (read($fh,my $buf,8192)) { print $buf; }
close $fh;
