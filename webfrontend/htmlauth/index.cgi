#!/usr/bin/perl
use strict;
use warnings;
use utf8;
use LoxBerry::System;
use LoxBerry::Web;

binmode STDOUT, ':encoding(UTF-8)';

# Forward the original form payload unchanged to the Python renderer as a
# query string. This avoids CGI-module dependencies while keeping POST forms.
my $method = uc($ENV{'REQUEST_METHOD'} // 'GET');
my $raw = '';
if ($method eq 'POST') {
    my $length = int($ENV{'CONTENT_LENGTH'} // 0);
    read(STDIN, $raw, $length) if $length > 0;
} else {
    $raw = $ENV{'QUERY_STRING'} // '';
}

local $ENV{'REQUEST_METHOD'} = 'GET';
local $ENV{'QUERY_STRING'} = $raw;
local $ENV{'LBPCONFIGDIR'} = $lbpconfigdir;
local $ENV{'LBPDATADIR'} = $lbpdatadir;
local $ENV{'LBPLOGDIR'} = $lbplogdir;
local $ENV{'LBPBINDIR'} = $lbpbindir;
local $ENV{'LBPTEMPLATEDIR'} = $lbptemplatedir;

my $python = '/usr/bin/python3';
my $script = "$lbpbindir/webui.py";
my $body = '';
if (open(my $fh, '-|', $python, $script)) {
    binmode $fh, ':encoding(UTF-8)';
    local $/;
    $body = <$fh> // '';
    close($fh);
} else {
    $body = '<div class="ui-state-error ui-corner-all" style="padding:1em">Weboberfläche konnte nicht gestartet werden.</div>';
}

LoxBerry::Web::lbheader('VELUX Active Connect', '', '');
print $body;
LoxBerry::Web::lbfooter();
